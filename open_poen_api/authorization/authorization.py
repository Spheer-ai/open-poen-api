import os
from oso import Oso, Relation
from oso.exceptions import ForbiddenError, NotFoundError
from .. import models as ent
from fastapi import HTTPException, Depends
from ..database import get_sync_session
from pydantic import BaseModel
from .data_adapter import SqlAlchemyAdapter
from sqlalchemy.orm import Session

SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = "HS256"

OSO = Oso()
OSO.register_class(
    ent.User,
    fields={
        "id": int,
        "is_superuser": bool,
        "role": str,
        "hidden": bool,
    },
)
OSO.register_class(
    ent.UserInitiativeRole,
    fields={
        "initiative": Relation(
            kind="one",
            other_type="Initiative",
            my_field="initiative_id",
            other_field="id",
        )
    },
)
OSO.register_class(
    ent.Initiative,
    fields={
        "user_roles": Relation(
            kind="many",
            other_type="UserInitiativeRole",
            my_field="id",
            other_field="initiative_id",
        ),
        "hidden": bool,
    },
)
OSO.register_class(
    ent.UserActivityRole,
    fields={
        "activity": Relation(
            kind="one",
            other_type="Activity",
            my_field="activity_id",
            other_field="id",
        )
    },
)
OSO.register_class(
    ent.Activity,
    fields={
        "user_roles": Relation(
            kind="many",
            other_type="UserActivityRole",
            my_field="id",
            other_field="activity_id",
        ),
        "hidden": bool,
        "initiative": Relation(
            kind="one",
            other_type="Initiative",
            my_field="initiative_id",
            other_field="id",
        ),
    },
)
OSO.register_class(
    ent.DebitCard,
    fields={
        "initiative": Relation(
            kind="one",
            other_type="Initiative",
            my_field="initiative_id",
            other_field="id",
        )
    },
)
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
    actor: ent.User | None, action: str, resource: ent.Base, oso: Oso
):
    oso_actor = get_oso_actor(actor)

    return oso.authorized_query(oso_actor, action, resource)


def is_allowed(actor: ent.User | None, action: str, resource: ent.Base):
    oso_actor = get_oso_actor(actor)

    return OSO.is_allowed(oso_actor, action, resource)


def authorize(actor: ent.User | None, action: str, resource: ent.Base, oso: Oso):
    """
    Authorizes a given user (actor) to perform an action on a resource
    if allowed by Oso's policies.
    """
    oso_actor = get_oso_actor(actor)

    try:
        OSO.authorize(oso_actor, action, resource)
    except (ForbiddenError, NotFoundError):
        raise HTTPException(status_code=403, detail="Not authorized")


def authorize_input_fields(
    actor: ent.User | None, action: str, resource: ent.Base, input_schema: BaseModel
):
    oso_actor = get_oso_actor(actor)
    fields = OSO.authorized_fields(oso_actor, action, resource)
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
    oso_actor = get_oso_actor(actor)

    degree1_fields = oso.authorized_fields(oso_actor, action, resource) - set(
        ignore_fields
    )
    degree2_fields = {}

    for rel_name, rel in resource.__mapper__.relationships.items():
        if rel_name in degree1_fields:
            related_class = rel.mapper.class_
            second_degree_rels = set(related_class.__mapper__.relationships.keys())
            related_class_fields = {
                i
                for i in oso.authorized_fields(
                    oso_actor, action, getattr(resource, rel_name)
                )
                if i not in second_degree_rels
            }
            degree2_fields[rel_name] = related_class_fields

    out_dict = {}
    for f in degree1_fields:
        val = getattr(resource, f)
        if f not in degree2_fields:
            out_dict[f] = val
        else:
            # Case of a single instance of a related model.
            if isinstance(val, ent.Base) and f in degree2_fields:
                out_dict[f] = {k: getattr(val, k) for k in degree2_fields[f]}
            # Case of a list of related models and of an empty list for a relationship
            # that's not loaded.
            elif isinstance(val, list) and f in degree2_fields:
                out_dict[f] = [
                    {k: getattr(i, k) for k in degree2_fields[f]} for i in val
                ]
            # Case of a non loaded scalar relationship.
            elif val is None:
                out_dict[f] = None
            else:
                raise ValueError("Relationship of unfamiliar type")

    return out_dict
