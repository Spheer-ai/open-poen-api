import os
from oso import Oso
from oso.exceptions import ForbiddenError, NotFoundError
from .schemas_and_models.models import entities as ent
from fastapi import HTTPException

SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = "HS256"


class Anon:
    pass


OSO = Oso()
OSO.register_class(ent.User)
OSO.register_class(Anon)
OSO.register_class(ent.Initiative)
OSO.load_file("open_poen_api/main.polar")


def get_oso_actor(actor: ent.User | None):
    """Because Oso works nicely with user defined classes, not with the None type."""
    return Anon if actor is None else actor


def authorize(actor: ent.User | None, action: str, resource: ent.Base):
    """
    Authorizes a given user (actor) to perform an action on a resource
    if allowed by Oso's policies.
    """
    oso_actor = get_oso_actor(actor)

    try:
        OSO.authorize(oso_actor, action, resource)
    except (ForbiddenError, NotFoundError):
        raise HTTPException(status_code=403, detail="Not authorized")


def select_authorized_fields(actor: ent.User | None, action: str, resource: ent.Base):
    """
    Filters the fields of a resource that an actor is authorized to access to give
    field-level access control as defined by Oso's policies.
    """
    oso_actor = get_oso_actor(actor)

    degree1_fields = OSO.authorized_fields(oso_actor, action, resource)
    degree2_fields = {}

    for rel_name, rel in resource.__mapper__.relationships.items():
        if rel_name in degree1_fields:
            related_class = rel.mapper.class_
            second_degree_rels = set(related_class.__mapper__.relationships.keys())
            related_class_fields = {
                i
                for i in OSO.authorized_fields(oso_actor, action, related_class)
                if i not in second_degree_rels
            }
            degree2_fields[rel_name] = related_class_fields

    out_dict = {}
    for f in degree1_fields:
        val = getattr(resource, f)
        if f not in degree2_fields:
            out_dict[f] = val
        else:
            if isinstance(val, ent.Base) and f in degree2_fields:
                out_dict[f] = {k: getattr(val, k) for k in degree2_fields[f]}
            elif isinstance(val, list) and f in degree2_fields:
                out_dict[f] = [
                    {k: getattr(i, k) for k in degree2_fields[f]} for i in val
                ]
            else:
                raise ValueError("Relationship of unfamiliar type")

    return out_dict
