from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, status, Response
from .database import get_session
from . import models as m
from . import authorization as auth
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from sqlalchemy.exc import IntegrityError
from .utils import get_entities_by_ids, temp_password_generator, get_fields_dict
from pydantic import ValidationError


router = APIRouter()


@router.post("/token", response_model=m.Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Session = Depends(get_session),
):
    user = auth.authenticate_user(form_data.username, form_data.password, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=15)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ACTIVITY
@router.post(
    "/initiative/{initiative_id}/activity",
    response_model=m.ActivityOutWithLinkedEntities,
    responses={
        404: {"description": "Initiative not found"},
        400: {"description": "Initiative already has an activity with this name"},
    },
)
async def create_activity(
    initiative_id: int,
    activity: m.ActivityIn,
    session: Session = Depends(get_session),
):
    initiative_db = session.get(m.Initiative, initiative_id)
    if not initiative_db:
        raise HTTPException(status_code=404, detail="Initiative not found")
    fields = get_fields_dict(activity)
    new_activity = m.Activity(initiative_id=initiative_id, **fields)
    if activity.activity_owner_ids is not None:
        new_activity.activity_owners = get_entities_by_ids(
            session, m.User, activity.activity_owner_ids
        )
    try:
        session.add(new_activity)
        session.commit()
        session.refresh(new_activity)
        return new_activity
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=400, detail="Initiative already has an activity with this name"
        )


@router.put(
    "/initiative/{initiative_id}/activity/{activity_id}",
    response_model=m.ActivityOutWithLinkedEntities,
)
async def update_activity(
    initiative_id: int,
    activity_id: int,
    activity: m.ActivityIn,
    session: Session = Depends(get_session),
):
    try:
        initiative_db = session.get(m.Initiative, initiative_id)
        activity_db = session.get(m.Activity, activity_id)

        if (
            not initiative_db
            or not activity_db
            or activity_db.initiative_id != initiative_id
        ):
            raise HTTPException(
                status_code=404, detail="Activity or Initiative not found"
            )

        fields = get_fields_dict(activity)
        for key, value in fields.items():
            setattr(activity_db, key, value)

        if activity.activity_owner_ids is not None:
            activity_db.activity_owners = get_entities_by_ids(
                session, m.User, activity.activity_owner_ids
            )

        session.add(activity_db)
        session.commit()
        session.refresh(activity_db)
        return activity_db
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Name already registered")


@router.delete("/initiative/{initiative_id}/activity/{activity_id}")
async def delete_activity(
    initiative_id: int,
    activity_id: int,
    session: Session = Depends(get_session),
):
    activity = session.get(m.Activity, activity_id)
    if not activity or activity.initiative_id != initiative_id:
        raise HTTPException(status_code=404, detail="Activity not found")

    session.delete(activity)
    session.commit()
    return Response(status_code=204)


@router.get(
    "/initiative/{initiative_id}/activities",
    response_model=m.ActivityOutList,
)
async def get_activities_by_initiative(
    initiative_id: int, session: Session = Depends(get_session)
):
    initiative = session.get(m.Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")

    activities = session.exec(
        select(m.Activity).where(m.Activity.initiative_id == initiative_id)
    ).all()
    return {"activities": activities}


# # ACTIVITY - PAYMENT
# @router.post("/initiative/{initiative_id}/activity/{activity_id}/payment")
# async def root(initiative_id: int, activity_id: int):
#     return {"amount": 10.01, "debitor": "Mark de Wijk"}


# @router.put("/initiative/{initiative_id}/activity/{activity_id}/payment/{payment_id}")
# async def root(initiative_id: int, activity_id: int, payment_id: int):
#     return {"amount": 10.01, "debitor": "Mark de Wijk"}


# @router.delete(
#     "/initiative/{initiative_id}/activity/{activity_id}/payment/{payment_id}"
# )
# async def root(initiative_id: int, activity_id: int, payment_id: int):
#     return {"status_code": 204, "content": "Succesfully deleted."}


# @router.get("/initiative/{initiative_id}/activity/{activity_id}/payments")
# async def root(initiative_id: int, activity_id: int):
#     return {"status_code": 200, "content": "to implement"}


# INITIATIVE
@router.post(
    "/initiative",
    response_model=m.InitiativeOutWithLinkedEntities,
    responses={400: {"description": "Name already registered"}},
)
async def create_initiative(
    initiative: m.InitiativeIn,
    session: Session = Depends(get_session),
):
    fields = get_fields_dict(initiative)
    new_initiative = m.Initiative(**fields)
    if initiative.initiative_owner_ids is not None:
        new_initiative.initiative_owners = get_entities_by_ids(
            session, m.User, initiative.initiative_owner_ids
        )
    if initiative.activity_ids is not None:
        new_initiative.activities = get_entities_by_ids(
            session, m.Activity, initiative.activity_ids
        )
    try:
        session.add(new_initiative)
        session.commit()
        session.refresh(new_initiative)
        return new_initiative
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Name already registered")


@router.put(
    "/initiative/{initiative_id}", response_model=m.InitiativeOutWithLinkedEntities
)
async def update_initiative(
    initiative_id: int,
    initiative: m.InitiativeIn,
    session: Session = Depends(get_session),
):
    initiative_db = session.get(m.Initiative, initiative_id)
    if not initiative_db:
        raise HTTPException(status_code=404, detail="Initiative not found")
    fields = get_fields_dict(initiative)
    for key, value in fields.items():
        setattr(initiative_db, key, value)
    if initiative.initiative_owner_ids is not None:
        initiative_db.initiative_owners = get_entities_by_ids(
            session, m.User, initiative.initiative_owner_ids
        )
    if initiative.activity_ids is not None:
        initiative_db.activities = get_entities_by_ids(
            session, m.Activity, initiative.activity_ids
        )
    try:
        session.add(initiative_db)
        session.commit()
        session.refresh(initiative_db)
        return initiative_db
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Name already registered")


@router.delete("/initiative/{initiative_id}")
async def delete_initiative(
    initiative_id: int, session: Session = Depends(get_session)
):
    initiative = session.get(m.Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")
    session.delete(initiative)
    session.commit()
    return Response(status_code=204)


@router.get("/initiatives", response_model=m.InitiativeOutList)
async def get_initiatives(session: Session = Depends(get_session)):
    # TODO: Enable searching by name, ordering by creation date and
    # initiative ownership.
    # TODO: pagination.
    initiatives = session.exec(select(m.Initiative)).all()
    return {"initiatives": initiatives}


@router.get("/initiatives/aggregate-numbers")
async def root():
    # TODO: Merge into /initiatives?
    # NOTE: Can't merge, because /initiatives will be paginated.
    return {"total_spent": 100, "total_earned": 100, "initiative_count": 22}


# # INITIATIVE - PAYMENT
# @router.post("/initiative/{initiative_id}/payment")
# async def root(initiative_id: int):
#     return {"amount": 10.01, "debitor": "Mark de Wijk"}


# @router.put("/initiative/{initiative_id}/payment/{payment_id}")
# async def root(initiative_id: int, payment_id: int):
#     return {"amount": 10.01, "debitor": "Mark de Wijk"}


# @router.delete("/initiative/{initiative_id}/payment/{payment_id}")
# async def root(initiative_id: int, payment_id: int):
#     return {"status_code": 204, "content": "Succesfully deleted."}


# @router.get("/initiative/{initiative_id}/payments")
# async def root(initiative_id: int):
#     return [
#         {"amount": 10.01, "debitor": "Mark de Wijk"},
#         {"amount": 9.01, "debitor": "Jamal Vleij"},
#     ]


# # INITIATIVE - DEBIT CARD
# @router.post("/initiative/{initiative_id}/debit-card")
# async def root(initiative_id: int):
#     return {"card_number": 12345678, "created_at": "2011-8-1"}


# @router.put("/initiative/{initiative_id}/debit-card/{debit_card_id}")
# async def root(initiative_id: int, debit_card_id: int):
#     # Use this to (de)couple a debit card from/to an initiative.
#     return {"card_number": 12345678, "created_at": "2011-8-1"}


# @router.get("/initiative/{initiative_id}/debit-cards")
# async def root(initiative_id: int):
#     return [
#         {"card_number": 12345678, "created_at": "2011-8-1"},
#         {"card_number": 12345679, "created_at": "2011-8-1"},
#     ]


# @router.get("/initiative/{initiative_id}/debit-cards/aggregate-numbers")
# async def root(initiative_id: int):
#     return [
#         {"card_number": 12345678, "received": 2000, "spent": 199},
#         {"card_number": 12345679, "received": 0, "spent": 0},
#     ]


# USER
@router.post("/user", response_model=m.UserOutputAdminWithLinkedEntities)
async def create_user(
    user: m.UserCreateAdmin,
    session: Session = Depends(get_session),
    requires_admin=Depends(auth.requires_admin),
):
    # TODO: Send an email with the temporary password. Otherwise
    # The user isn't notified and he can't login!
    # TODO: Route for resetting the password.
    temp_password = temp_password_generator()
    fields = get_fields_dict(user.dict())
    new_user = m.User(**fields, hashed_password=auth.PWD_CONTEXT.hash(temp_password))
    if user.initiative_ids is not None:
        new_user.initiatives = get_entities_by_ids(
            session, m.Initiative, user.initiative_ids
        )
    if user.activity_ids is not None:
        new_user.activities = get_entities_by_ids(
            session, m.Activity, user.activity_ids
        )
    try:
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return m.UserOutputAdminWithLinkedEntities.from_orm(new_user)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Email address already registered")


@router.patch("/user/{user_id}", response_model=m.UserOutputAdminWithLinkedEntities)
async def update_user(
    user_id: int,
    user: m.UserUpdateAdmin,
    requires_login=Depends(auth.requires_login),
    session: Session = Depends(get_session),
    auth_levels: list[auth.AuthLevel] = Depends(auth.get_authorization_level),
):
    user_db = session.get(m.User, user_id)
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")

    auth.validate_input_data(
        unified_input_schema=user,
        parse_schemas=[
            (auth.AuthLevel.ADMIN, m.UserUpdateAdmin),
            (auth.AuthLevel.USER_OWNER, m.UserUpdateUser),
        ],
        auth_levels=auth_levels,
    )

    fields = get_fields_dict(user.dict(exclude_unset=True))
    for key, value in fields.items():
        setattr(user_db, key, value)
    if user.initiative_ids is not None:
        user_db.initiatives = get_entities_by_ids(
            session, m.Initiative, user.initiative_ids
        )
    if user.activity_ids is not None:
        user_db.activities = get_entities_by_ids(session, m.Activity, user.activity_ids)
    try:
        session.add(user_db)
        session.commit()
        session.refresh(user_db)
        return auth.validate_output_data(
            user_db,
            parse_schemas=[
                (auth.AuthLevel.ADMIN, m.UserOutputAdminWithLinkedEntities),
                (auth.AuthLevel.USER_OWNER, m.UserOutputUserWithLinkedEntities),
            ],
            auth_levels=auth_levels,
        )
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Email address already registered")


@router.delete("/user/{user_id}")
async def delete_user(
    user_id: int,
    requires_admin=Depends(auth.requires_admin),
    session: Session = Depends(get_session),
):
    user = session.get(m.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    session.delete(user)
    session.commit()
    return Response(status_code=204)


@router.get("/users", response_model=m.UserOutputUserList)
def get_users(session: Session = Depends(get_session)):
    # TODO: Enable searching by email.
    # TODO: pagination.
    users = session.exec(select(m.User)).all()
    return {"users": users}


# # FUNDER
# @router.post("/funder")
# async def root():
#     # If we continue linking to initiatives, we need to add such a query param.
#     return {"name": "Gemeente Amsterdam", "created_at": "2022-4-1"}


# @router.put("/funder/{funder_id}")
# async def root(funder_id: int):
#     return {"name": "Gemeente Amsterdam", "created_at": "2022-4-1"}


# @router.delete("/funder/{funder_id}")
# async def root(funder_id: int):
#     return {"status_code": 204, "content": "Succesfully deleted."}


# @router.get("/funders")
# async def root():
#     # If we continue linking to initiatives, we need to add such a query param.
#     return [
#         {"name": "Gemeente Amsterdam", "created_at": "2022-4-1"},
#         {"name": "Stichting Leergeld", "created_at": "2022-1-1"},
#     ]


# # BNG
# @router.post("/bng-connection")
# async def root():
#     # Should accept IBAN and only available to admins.
#     return {"IBAN": "NL32INGB00039845938"}


# @router.delete("/bng-connection")
# async def root():
#     return {"status_code": 204, "content": "Succesfully deleted."}


# @router.get("/bng-connection")
# async def root():
#     # Only available to admins.
#     return {"IBAN": "NL32INGB00039845938"}


# @router.get("/bng-connection/status")
# async def root():
#     return {
#         "present": True,
#         "online": True,
#         "days_left": 33,
#         "last_sync": "2022-12-1, 17:53",
#     }
