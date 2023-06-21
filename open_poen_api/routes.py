from sqlmodel import Session, select
from fastapi import APIRouter, Depends, HTTPException, status, Response
from .database import get_session
from .schemas_and_models.models import entities as e
from .schemas_and_models import linked_entities as le
from .schemas_and_models.authorization import Token
from . import schemas_and_models as s
from . import authorization as auth
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from sqlalchemy.exc import IntegrityError
from .utils import get_entities_by_ids, temp_password_generator, get_fields_dict
from pydantic import ValidationError


router = APIRouter()


@router.post("/token", response_model=Token)
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
    response_model=le.ActivityOutputAdminWithLinkedEntities,
    responses={
        404: {"description": "Initiative not found"},
        400: {"description": "Initiative already has an activity with this name"},
    },
)
async def create_activity(
    initiative_id: int,
    activity: s.ActivityCreateInitiativeOwner,
    requires_log_in=Depends(auth.requires_login),
    requires_initiative_owner=Depends(auth.requires_initiative_owner),
    auth_levels: list[auth.AuthLevel] = Depends(auth.get_authorization_levels),
    session: Session = Depends(get_session),
):
    initiative_db = session.get(e.Initiative, initiative_id)
    if not initiative_db:
        raise HTTPException(status_code=404, detail="Initiative not found")

    fields = get_fields_dict(activity.dict())
    new_activity = e.Activity(initiative_id=initiative_id, **fields)
    if activity.activity_owner_ids is not None:
        new_activity.activity_owners = get_entities_by_ids(
            session, e.User, activity.activity_owner_ids
        )
    try:
        session.add(new_activity)
        session.commit()
        session.refresh(new_activity)
        return auth.validate_output_schema(
            new_activity,
            parse_schemas=[
                (auth.AuthLevel.ADMIN, le.ActivityOutputAdminWithLinkedEntities),
                (
                    auth.AuthLevel.INITIATIVE_OWNER,
                    le.ActivityOutputInitiativeOwnerWithLinkedEntities,
                ),
            ],
            auth_levels=auth_levels,
        )
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=400, detail="Initiative already has an activity with this name"
        )


@router.patch(
    "/initiative/{initiative_id}/activity/{activity_id}",
    response_model=le.ActivityOutputAdminWithLinkedEntities,
    response_model_exclude_unset=True,
)
async def update_activity(
    initiative_id: int,
    activity_id: int,
    activity: s.ActivityUpdateInitiativeOwner,
    requires_login=Depends(auth.requires_login),
    requires_initiative_owner=Depends(auth.requires_initiative_owner),
    session: Session = Depends(get_session),
    auth_levels: list[auth.AuthLevel] = Depends(auth.get_authorization_levels),
):
    try:
        initiative_db = session.get(e.Initiative, initiative_id)
        activity_db = session.get(e.Activity, activity_id)

        if (
            not initiative_db
            or not activity_db
            or activity_db.initiative_id != initiative_id
        ):
            raise HTTPException(
                status_code=404, detail="Activity or Initiative not found"
            )

        fields = get_fields_dict(activity.dict(exclude_unset=True))
        for key, value in fields.items():
            setattr(activity_db, key, value)

        if activity.activity_owner_ids is not None:
            activity_db.activity_owners = get_entities_by_ids(
                session, e.User, activity.activity_owner_ids
            )

        session.add(activity_db)
        session.commit()
        session.refresh(activity_db)
        return auth.validate_output_schema(
            activity_db,
            parse_schemas=[
                (auth.AuthLevel.ADMIN, le.ActivityOutputAdminWithLinkedEntities),
                (
                    auth.AuthLevel.INITIATIVE_OWNER,
                    le.ActivityOutputInitiativeOwnerWithLinkedEntities,
                ),
            ],
            auth_levels=auth_levels,
        )
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Name already registered")


@router.delete("/initiative/{initiative_id}/activity/{activity_id}")
async def delete_activity(
    initiative_id: int,
    activity_id: int,
    requires_initiative_owner=Depends(auth.requires_initiative_owner),
    session: Session = Depends(get_session),
):
    activity = session.get(e.Activity, activity_id)
    if not activity or activity.initiative_id != initiative_id:
        raise HTTPException(status_code=404, detail="Activity not found")

    session.delete(activity)
    session.commit()
    return Response(status_code=204)


@router.get(
    "/initiative/{initiative_id}/activities",
    response_model=s.ActivityOutputAdminList,
)
async def get_activities_by_initiative(
    initiative_id: int,
    session: Session = Depends(get_session),
    auth_levels: list[auth.AuthLevel] = Depends(auth.get_authorization_levels),
):
    initiative = session.get(e.Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")

    activities = session.exec(
        select(e.Activity).where(e.Activity.initiative_id == initiative_id)
    ).all()
    parsed_activities = auth.validate_output_schema(
        activities,
        parse_schemas=[
            (auth.AuthLevel.ADMIN, s.ActivityOutputAdminList),
            (auth.AuthLevel.INITIATIVE_OWNER, s.ActivityOutputInitiativeOwnerList),
            (auth.AuthLevel.GUEST, s.ActivityOutputGuestList),
        ],
        auth_levels=auth_levels,
        seq_key="activities",
    )
    return parsed_activities


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
    response_model=le.InitiativeOutputAdminWithLinkedEntities,
    responses={400: {"description": "Name already registered"}},
)
async def create_initiative(
    initiative: s.InitiativeCreateAdmin,
    requires_admin=Depends(auth.requires_admin),
    session: Session = Depends(get_session),
):
    fields = get_fields_dict(initiative.dict())
    new_initiative = e.Initiative(**fields)
    if initiative.initiative_owner_ids is not None:
        new_initiative.initiative_owners = get_entities_by_ids(
            session, e.User, initiative.initiative_owner_ids
        )
    # TODO: Remove this.
    if initiative.activity_ids is not None:
        new_initiative.activities = get_entities_by_ids(
            session, e.Activity, initiative.activity_ids
        )
    try:
        session.add(new_initiative)
        session.commit()
        session.refresh(new_initiative)
        return le.InitiativeOutputAdminWithLinkedEntities.from_orm(new_initiative)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Name already registered")


@router.patch(
    "/initiative/{initiative_id}",
    response_model=le.InitiativeOutputAdminWithLinkedEntities,
    response_model_exclude_unset=True,
)
async def update_initiative(
    initiative_id: int,
    initiative: s.InitiativeUpdateAdmin,
    requires_login=Depends(auth.requires_login),
    session: Session = Depends(get_session),
    auth_levels: list[auth.AuthLevel] = Depends(auth.get_authorization_levels),
):
    initiative_db = session.get(e.Initiative, initiative_id)
    if not initiative_db:
        raise HTTPException(status_code=404, detail="Initiative not found")

    auth.validate_input_schema(
        unified_input_schema=initiative,
        parse_schemas=[
            (auth.AuthLevel.ADMIN, s.InitiativeUpdateAdmin),
            (auth.AuthLevel.INITIATIVE_OWNER, s.InitiativeUpdateInitiativeOwner),
        ],
        auth_levels=auth_levels,
    )

    fields = get_fields_dict(initiative.dict(exclude_unset=True))
    for key, value in fields.items():
        setattr(initiative_db, key, value)
    if initiative.initiative_owner_ids is not None:
        initiative_db.initiative_owners = get_entities_by_ids(
            session, e.User, initiative.initiative_owner_ids
        )
    if initiative.activity_ids is not None:
        initiative_db.activities = get_entities_by_ids(
            session, e.Activity, initiative.activity_ids
        )
    try:
        session.add(initiative_db)
        session.commit()
        session.refresh(initiative_db)
        return auth.validate_output_schema(
            initiative_db,
            parse_schemas=[
                (auth.AuthLevel.ADMIN, le.InitiativeOutputAdminWithLinkedEntities),
                (
                    auth.AuthLevel.ACTIVITY_OWNER,  # TODO: Make this InitiativeOutputInitiativeOwnerWithLinkedEntities?
                    le.InitiativeOutputActivityOwnerWithLinkedEntities,
                ),
            ],
            auth_levels=auth_levels,
        )
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Name already registered")


@router.delete("/initiative/{initiative_id}")
async def delete_initiative(
    initiative_id: int,
    requires_admin=Depends(auth.requires_admin),
    session: Session = Depends(get_session),
):
    initiative = session.get(e.Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")

    session.delete(initiative)
    session.commit()
    return Response(status_code=204)


@router.get(
    "/initiatives",
    response_model=s.InitiativeOutputAdminList,
    response_model_exclude_unset=True,
)
async def get_initiatives(
    session: Session = Depends(get_session),
    auth_levels: list[auth.AuthLevel] = Depends(auth.get_authorization_levels),
):
    # TODO: Enable searching by name, ordering by creation date and
    # initiative ownership.
    # TODO: pagination.
    initiatives = session.exec(select(e.Initiative)).all()
    parsed_initiatives = auth.validate_output_schema(
        initiatives,
        parse_schemas=[
            (auth.AuthLevel.ADMIN, s.InitiativeOutputAdminList),
            (auth.AuthLevel.GUEST, s.InitiativeOutputGuestList),
        ],
        auth_levels=auth_levels,
        seq_key="initiatives",
    )
    return parsed_initiatives


@router.get("/initiatives/aggregate-numbers")
async def root():
    # TODO: Merge into /initiatives?
    # NOTE: Can't merge, because /initiatives will be paginated.
    # TODO: Implement caching to prevent calculating this with every
    # front page view?
    return {"total_spent": 100, "total_earned": 100, "initiative_count": 22}


# # INITIATIVE - PAYMENT
@router.post(
    "/initiative/{initiative_id}/payment",
    response_model=le.PaymentOutputFinancialWithLinkedEntities,
    responses={404: {"description": "Initiative not found"}},
)
async def create_initiative_payment(
    initiative_id: int,
    payment: s.PaymentCreateFinancial,
    requires_login=Depends(auth.requires_login),
    requires_financial=Depends(auth.requires_financial),
    session: Session = Depends(get_session),
):
    initiative_db = session.get(e.Initiative, initiative_id)
    if not initiative_db:
        raise HTTPException(status_code=404, detail="Initiative not found")

    fields = get_fields_dict(payment.dict())
    new_payment = e.Payment(initiative_id=initiative_id, **fields)
    try:
        session.add(new_payment)
        session.commit()
        session.refresh(new_payment)
        return le.PaymentOutputFinancialWithLinkedEntities.from_orm(new_payment)
    except Exception:
        session.rollback()
        raise Exception


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
@router.post("/user", response_model=le.UserOutputAdminWithLinkedEntities)
async def create_user(
    user: s.UserCreateAdmin,
    session: Session = Depends(get_session),
    requires_admin=Depends(auth.requires_admin),
):
    # TODO: Send an email with the temporary password. Otherwise
    # The user isn't notified and he can't login!
    # TODO: Route for resetting the password.
    temp_password = temp_password_generator()
    fields = get_fields_dict(user.dict())
    new_user = e.User(**fields, hashed_password=auth.PWD_CONTEXT.hash(temp_password))
    if user.initiative_ids is not None:
        new_user.initiatives = get_entities_by_ids(
            session, e.Initiative, user.initiative_ids
        )
    if user.activity_ids is not None:
        new_user.activities = get_entities_by_ids(
            session, e.Activity, user.activity_ids
        )
    try:
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return le.UserOutputAdminWithLinkedEntities.from_orm(new_user)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Email address already registered")


@router.patch(
    "/user/{user_id}",
    response_model=le.UserOutputAdminWithLinkedEntities,
    response_model_exclude_unset=True,
)
@router.patch("/user/{user_id}")
async def update_user(
    user_id: int,
    user: s.UserUpdateAdmin,
    requires_login=Depends(auth.requires_login),
    session: Session = Depends(get_session),
    auth_levels: list[auth.AuthLevel] = Depends(auth.get_authorization_levels),
):
    user_db = session.get(e.User, user_id)
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")

    auth.validate_input_schema(
        unified_input_schema=user,
        parse_schemas=[
            (auth.AuthLevel.ADMIN, s.UserUpdateAdmin),
            (auth.AuthLevel.USER_OWNER, s.UserUpdateUserOwner),
        ],
        auth_levels=auth_levels,
    )

    fields = get_fields_dict(user.dict(exclude_unset=True))
    for key, value in fields.items():
        setattr(user_db, key, value)
    if user.initiative_ids is not None:
        user_db.initiatives = get_entities_by_ids(
            session, e.Initiative, user.initiative_ids
        )
    if user.activity_ids is not None:
        user_db.activities = get_entities_by_ids(session, e.Activity, user.activity_ids)
    try:
        session.add(user_db)
        session.commit()
        session.refresh(user_db)
        return auth.validate_output_schema(
            user_db,
            parse_schemas=[
                (auth.AuthLevel.ADMIN, le.UserOutputAdminWithLinkedEntities),
                (auth.AuthLevel.USER_OWNER, le.UserOutputUserOwnerWithLinkedEntities),
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
    user = session.get(e.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    session.delete(user)
    session.commit()
    return Response(status_code=204)


@router.get(
    "/users", response_model=s.UserOutputAdminList, response_model_exclude_unset=True
)
def get_users(
    session: Session = Depends(get_session),
    requires_login=Depends(auth.requires_login),
    auth_levels: list[auth.AuthLevel] = Depends(auth.get_authorization_levels),
):
    # TODO: Enable searching by email.
    # TODO: pagination.
    users = session.exec(select(e.User)).all()
    parsed_users = auth.validate_output_schema(
        users,
        parse_schemas=[
            (auth.AuthLevel.ADMIN, s.UserOutputAdminList),
            (auth.AuthLevel.USER, s.UserOutputUserList),
        ],
        auth_levels=auth_levels,
        seq_key="users",
    )
    return parsed_users


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
