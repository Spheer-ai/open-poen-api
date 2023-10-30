import os
from oso import Oso, Relation
from oso.exceptions import ForbiddenError, NotFoundError
from .. import models as ent
from fastapi import HTTPException, Depends
from ..database import get_sync_session
from pydantic import BaseModel
from .data_adapter import SqlAlchemyAdapter
from sqlalchemy.orm import Session
from typing import Type
from sqlalchemy.ext.associationproxy import _AssociationList

SECRET_KEY = os.environ["SECRET_KEY"]
ALGORITHM = "HS256"

OSO = Oso()
OSO.register_class(ent.Funder)
OSO.register_class(ent.Regulation)
OSO.register_class(ent.Attachment)
OSO.register_class(ent.User)
OSO.register_class(ent.Initiative)
OSO.register_class(ent.Activity)
OSO.register_class(ent.DebitCard)
OSO.register_class(ent.Grant)
OSO.register_class(ent.BankAccount)
OSO.register_class(ent.Payment)
OSO.load_files(["open_poen_api/main.polar"])


async def set_sqlalchemy_adapter(session: Session = Depends(get_sync_session)):
    # You'll only need this when calling get_authorized_output_fields on a resource
    # that has rules for established relationships.
    OSO.set_data_filtering_adapter(SqlAlchemyAdapter(session))
    yield OSO


def get_oso_actor(actor: ent.User | None):
    """Because Oso works nicely with user defined classes, not with the None type."""
    anon = ent.User(id=-1, role="anon", is_superuser=False)
    return anon if actor is None else actor


def get_authorized_query(
    actor: ent.User | None, action: str, resource: Type[ent.Base], oso: Oso
):
    oso_actor = get_oso_actor(actor)

    return oso.authorized_query(oso_actor, action, resource)


def get_authorized_actions(actor: ent.User | None, resource: ent.Base | str, oso: Oso):
    oso_actor = get_oso_actor(actor)

    return oso.authorized_actions(oso_actor, resource)


def is_allowed(actor: ent.User | None, action: str, resource: ent.Base):
    oso_actor = get_oso_actor(actor)

    return OSO.is_allowed(oso_actor, action, resource)


def authorize(
    actor: ent.User | None,
    action: str,
    resource: ent.Base | str | Type[ent.Base],
    oso: Oso,
):
    """
    Authorizes a given user (actor) to perform an action on a resource
    if allowed by Oso's policies.
    """
    oso_actor = get_oso_actor(actor)

    try:
        OSO.authorize(oso_actor, action, resource)
    except (ForbiddenError, NotFoundError):
        raise HTTPException(status_code=403, detail="Not authorized")


def get_authorized_fields(actor: ent.User | None, action: str, resource: ent.Base):
    oso_actor = get_oso_actor(actor)
    return OSO.authorized_fields(oso_actor, action, resource)


def authorize_input_fields(
    actor: ent.User | None, action: str, resource: ent.Base, input_schema: BaseModel
):
    fields = get_authorized_fields(actor, action, resource)
    if not all([k in fields for k in input_schema.dict(exclude_unset=True).keys()]):
        raise HTTPException(status_code=403, detail="Not authorized")


def get_authorized_output_fields(
    actor: ent.User | None,
    action: str,
    resource: ent.Base,
    oso: Oso,
    ignore_fields: list[str] = [],
):
    """
    Filters the fields of a resource that an actor is authorized to access to give
    field-level access control as defined by Oso's policies. It filters the first
    degree fields of resource itself and the second degree fields of relationships
    of resource, but makes sure to not include relationships of relationships.

    This function also works for resources that have its relationships not loaded.
    In that case, scalar relationships have a value of None and list relationships
    are an emtpy list. These fields in that case remain as they are.
    """

    def get_fields_for_relationship(resource: ent.Base):
        fields = oso.authorized_fields(oso_actor, action, resource)
        filtered_fields = (
            fields
            - set(resource.PROXIES)
            - set(resource.__mapper__.relationships.keys())
        )
        fields_with_values = {}
        for f in filtered_fields:
            fields_with_values[f] = getattr(resource, f)
        return fields_with_values

    oso_actor = get_oso_actor(actor)
    allowed_fields = oso.authorized_fields(oso_actor, action, resource) - set(
        ignore_fields
    )

    # Non relationship fields that are authorized.
    non_rel_fields = (
        allowed_fields
        - set(resource.PROXIES)
        - set(resource.__mapper__.relationships.keys())
    )
    # Relationship fields that are authorized.
    rel_fields = allowed_fields & (
        set(resource.PROXIES) | set(resource.__mapper__.relationships.keys())
    )
    assert non_rel_fields | rel_fields == allowed_fields

    # Fetch non relationship fields.
    result = {f: getattr(resource, f) for f in non_rel_fields}

    # Handle relationship fields.
    for f in rel_fields:
        rel = getattr(resource, f)
        if isinstance(rel, ent.Base):
            if is_allowed(actor, action, rel):
                result[f] = get_fields_for_relationship(rel)
        elif isinstance(rel, (list, _AssociationList)):
            result[f] = [
                get_fields_for_relationship(i)
                for i in rel
                if is_allowed(actor, action, i)
            ]
        elif rel is None:
            result[f] = rel
        else:
            raise ValueError(f"Unexpected relationship type for field {f}")

    return result
