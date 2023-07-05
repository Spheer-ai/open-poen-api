from sqlmodel import Session, select, and_
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Response,
    Query,
    BackgroundTasks,
)
from fastapi.responses import RedirectResponse
from .database import get_session
from .schemas_and_models.models import entities as ent
from .schemas_and_models import linked_entities as le
from .schemas_and_models.authorization import Token
from . import schemas_and_models as s
from . import authorization as auth
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime
from sqlalchemy.exc import IntegrityError
from .utils.utils import (
    get_entities_by_ids,
    temp_password_generator,
    get_fields_dict,
    get_requester_ip,
    format_user_timestamp,
)
from .payment import check_for_forbidden_fields
from jose import jwt, JWTError, ExpiredSignatureError
from time import time
import pytz
import os

from .bng import get_bng_payments, retrieve_access_token, create_consent
from .gocardless import refresh_tokens, client
from requests.exceptions import RequestException

DOMAIN_NAME = os.environ.get("DOMAIN_NAME")


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
    requires_initiative_owner=Depends(auth.requires_initiative_owner),
    auth_levels: list[auth.AuthLevel] = Depends(auth.get_initiative_auth_levels()),
    session: Session = Depends(get_session),
):
    initiative_db = session.get(ent.Initiative, initiative_id)
    if not initiative_db:
        raise HTTPException(status_code=404, detail="Initiative not found")

    fields = get_fields_dict(activity.dict())
    new_activity = ent.Activity(initiative_id=initiative_id, **fields)
    if activity.activity_owner_ids is not None:
        new_activity.activity_owners = get_entities_by_ids(
            session, ent.User, activity.activity_owner_ids
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
    requires_initiative_owner=Depends(auth.requires_initiative_owner),
    session: Session = Depends(get_session),
    auth_levels: list[auth.AuthLevel] = Depends(auth.get_initiative_auth_levels()),
):
    try:
        initiative_db = session.get(ent.Initiative, initiative_id)
        activity_db = session.get(ent.Activity, activity_id)

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
                session, ent.User, activity.activity_owner_ids
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
    activity = session.get(ent.Activity, activity_id)
    if not activity or activity.initiative_id != initiative_id:
        raise HTTPException(status_code=404, detail="Activity not found")

    session.delete(activity)
    session.commit()
    return Response(status_code=204)


@router.get(
    "/initiative/{initiative_id}/activities",
    response_model=s.ActivityOutputAdminList,
    response_model_exclude_unset=True,
)
async def get_activities_by_initiative(
    initiative_id: int,
    session: Session = Depends(get_session),
    auth_levels: list[auth.AuthLevel] = Depends(auth.get_initiative_auth_levels()),
):
    initiative = session.get(ent.Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")

    activities = session.exec(
        select(ent.Activity).where(ent.Activity.initiative_id == initiative_id)
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
@router.post(
    "/initiative/{initiative_id}/activity/{activity_id}/payment",
    response_model=le.PaymentOutputFinancialWithLinkedEntities,
    responses={404: {"description": "Initiative or Activity not found"}},
)
async def root(
    initiative_id: int,
    activity_id: int,
    payment: s.PaymentCreateFinancial,
    requires_financial=Depends(auth.requires_financial),
    session: Session = Depends(get_session),
):
    initiative_db = session.get(ent.Initiative, initiative_id)
    activity_db = session.get(ent.Activity, activity_id)

    if (
        not initiative_db
        or not activity_db
        or activity_db not in initiative_db.activities
    ):
        raise HTTPException(status_code=404, detail="Initiative or Activity not found")

    fields = get_fields_dict(payment.dict())
    new_payment = ent.Payment(
        initiative_id=initiative_id, activity_id=activity_id, **fields
    )
    session.add(new_payment)
    session.commit()
    session.refresh(new_payment)
    return le.PaymentOutputFinancialWithLinkedEntities.from_orm(new_payment)


@router.patch(
    "/initiative/{initiative_id}/activity/{activity_id}/payment/{payment_id}",
    response_model=le.PaymentOutputFinancialWithLinkedEntities,
    responses={404: {"description": "Initiative, Activity or Payment not found"}},
)
async def update_activity_payment(
    initiative_id: int,
    activity_id: int,
    payment_id: int,
    payment: s.PaymentUpdateFinancial,
    session: Session = Depends(get_session),
    auth_levels: list[auth.AuthLevel] = Depends(
        auth.get_initiative_auth_levels(requires_login=True)
    ),
):
    initiative_db = session.get(ent.Initiative, initiative_id)
    activity_db = session.get(ent.Activity, activity_id)
    payment_db = session.get(ent.Payment, payment_id)
    if (
        not initiative_db
        or not activity_db
        or not payment_db
        or payment_db not in activity_db.payments
        or activity_db not in initiative_db.activities
    ):
        raise HTTPException(
            status_code=404, detail="Initiative, Activity or Payment not found"
        )

    auth.validate_input_schema(
        unified_input_schema=payment,
        parse_schemas=[
            (auth.AuthLevel.FINANCIAL, s.PaymentUpdateFinancial),
            (auth.AuthLevel.INITIATIVE_OWNER, s.PaymentUpdateInitiativeOwner),
            (auth.AuthLevel.ACTIVITY_OWNER, s.PaymentUpdateActivityOwner),
        ],
        auth_levels=auth_levels,
    )

    fields = get_fields_dict(payment.dict(exclude_unset=True))
    check_for_forbidden_fields(payment_db, fields)

    for key, value in fields.items():
        setattr(payment_db, key, value)

    session.add(payment_db)
    session.commit()
    session.refresh(payment_db)
    return payment_db


@router.delete(
    "/initiative/{initiative_id}/activity/{activity_id}/payment/{payment_id}"
)
async def delete_activity_payment(
    initiative_id: int,
    activity_id: int,
    payment_id: int,
    requires_financial=Depends(auth.requires_financial),
    session: Session = Depends(get_session),
):
    initiative_db = session.get(ent.Initiative, initiative_id)
    activity_db = session.get(ent.Activity, activity_id)
    payment_db = session.get(ent.Payment, payment_id)
    if (
        not initiative_db
        or not activity_db
        or not payment_db
        or payment_db not in activity_db.payments
        or activity_db not in initiative_db.activities
    ):
        raise HTTPException(
            status_code=404, detail="Initiative, Activity or Payment not found"
        )

    session.delete(payment_db)
    session.commit()
    return Response(status_code=204)


@router.get(
    "/initiative/{initiative_id}/activity/{activity_id}/payments",
    response_model=s.PaymentOutputFinancialList,
    response_model_exclude_unset=True,
)
async def get_activity_payments(
    initiative_id: int,
    activity_id: int,
    session: Session = Depends(get_session),
    auth_levels: list[auth.AuthLevel] = Depends(auth.get_initiative_auth_levels()),
):
    # TODO: Enable ordering by created_at or booking date or something.
    # TODO: Enable pagination.
    # TODO: Add linking logic for BNG, NORDIGEN
    payments = session.exec(
        select(ent.Payment).where(
            and_(
                ent.Payment.initiative_id == initiative_id,
                ent.Payment.activity_id == activity_id,
            )
        )
    ).all()
    parsed_payments = auth.validate_output_schema(
        payments,
        parse_schemas=[
            (auth.AuthLevel.FINANCIAL, s.PaymentOutputFinancialList),
            (auth.AuthLevel.INITIATIVE_OWNER, s.PaymentOutputInitiatitveOwnerList),
            (auth.AuthLevel.GUEST, s.PaymentOutputGuestList),
        ],
        auth_levels=auth_levels,
        seq_key="payments",
    )
    return parsed_payments


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
    new_initiative = ent.Initiative(**fields)
    if initiative.initiative_owner_ids is not None:
        new_initiative.initiative_owners = get_entities_by_ids(
            session, ent.User, initiative.initiative_owner_ids
        )
    # TODO: Remove this.
    if initiative.activity_ids is not None:
        new_initiative.activities = get_entities_by_ids(
            session, ent.Activity, initiative.activity_ids
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
    session: Session = Depends(get_session),
    auth_levels: list[auth.AuthLevel] = Depends(
        auth.get_initiative_auth_levels(requires_login=True)
    ),
):
    initiative_db = session.get(ent.Initiative, initiative_id)
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
            session, ent.User, initiative.initiative_owner_ids
        )
    if initiative.activity_ids is not None:
        initiative_db.activities = get_entities_by_ids(
            session, ent.Activity, initiative.activity_ids
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
                    auth.AuthLevel.INITIATIVE_OWNER,
                    le.InitiativeOutputInitiativeOwnerWithLinkedEntities,
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
    initiative = session.get(ent.Initiative, initiative_id)
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
    auth_levels: list[auth.AuthLevel] = Depends(auth.get_initiative_auth_levels()),
):
    # TODO: Enable searching by name, ordering by creation date and
    # initiative ownership.
    # TODO: pagination.
    initiatives = session.exec(select(ent.Initiative)).all()
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


# @router.get("/initiatives/aggregate-numbers")
# async def root():
# TODO: Merge into /initiatives?
# NOTE: Can't merge, because /initiatives will be paginated.
# TODO: Implement caching to prevent calculating this with every
# front page view?
# return {"total_spent": 100, "total_earned": 100, "initiative_count": 22}


# INITIATIVE - PAYMENT
@router.post(
    "/initiative/{initiative_id}/payment",
    response_model=le.PaymentOutputFinancialWithLinkedEntities,
    responses={404: {"description": "Initiative not found"}},
)
async def create_initiative_payment(
    initiative_id: int,
    payment: s.PaymentCreateFinancial,
    requires_financial=Depends(auth.requires_financial),
    session: Session = Depends(get_session),
):
    initiative_db = session.get(ent.Initiative, initiative_id)
    if not initiative_db:
        raise HTTPException(status_code=404, detail="Initiative not found")

    fields = get_fields_dict(payment.dict())
    new_payment = ent.Payment(initiative_id=initiative_id, **fields)
    session.add(new_payment)
    session.commit()
    session.refresh(new_payment)
    return le.PaymentOutputFinancialWithLinkedEntities.from_orm(new_payment)


@router.patch(
    "/initiative/{initiative_id}/payment/{payment_id}",
    response_model=le.PaymentOutputFinancialWithLinkedEntities,
    responses={
        404: {"description": "Initiative or Payment not found"},
        403: {
            "description": "Returned if you change forbidden fields on non manual payments."
        },
    },
)
async def update_initiative_payment(
    initiative_id: int,
    payment_id: int,
    payment: s.PaymentUpdateFinancial,
    session: Session = Depends(get_session),
    auth_levels: list[auth.AuthLevel] = Depends(
        auth.get_initiative_auth_levels(requires_login=True)
    ),
):
    initiative_db = session.get(ent.Initiative, initiative_id)
    payment_db = session.get(ent.Payment, payment_id)

    if not initiative_db or not payment_db or payment_db not in initiative_db.payments:
        raise HTTPException(status_code=404, detail="Initiative or Payment not found")

    auth.validate_input_schema(
        unified_input_schema=payment,
        parse_schemas=[
            (auth.AuthLevel.FINANCIAL, s.PaymentUpdateFinancial),
            (auth.AuthLevel.INITIATIVE_OWNER, s.PaymentUpdateInitiativeOwner),
        ],
        auth_levels=auth_levels,
    )

    fields = get_fields_dict(payment.dict(exclude_unset=True))
    check_for_forbidden_fields(payment_db, fields)

    for key, value in fields.items():
        setattr(payment_db, key, value)

    session.add(payment_db)
    session.commit()
    session.refresh(payment_db)
    return payment_db


@router.delete("/initiative/{initiative_id}/payment/{payment_id}")
async def delete_initiative_payment(
    initiative_id: int,
    payment_id: int,
    requires_financial=Depends(auth.requires_financial),
    session: Session = Depends(get_session),
):
    initiative_db = session.get(ent.Initiative, initiative_id)
    payment_db = session.get(ent.Payment, payment_id)

    if not initiative_db or not payment_db or payment_db not in initiative_db.payments:
        raise HTTPException(status_code=404, detail="Initiative or Payment not found")

    session.delete(payment_db)
    session.commit()
    return Response(status_code=204)


@router.get(
    "/initiative/{initiative_id}/payments",
    response_model=s.PaymentOutputFinancialList,
    response_model_exclude_unset=True,
)
async def get_initiative_payments(
    initiative_id: int,
    session: Session = Depends(get_session),
    auth_levels: list[auth.AuthLevel] = Depends(auth.get_initiative_auth_levels()),
):
    # TODO: Enable ordering by created_at or booking date or something.
    # TODO: Enable pagination.
    # TODO: Add linking logic for BNG, NORDIGEN
    payments = session.exec(
        select(ent.Payment).where(ent.Payment.initiative_id == initiative_id)
    ).all()
    parsed_payments = auth.validate_output_schema(
        payments,
        parse_schemas=[
            (auth.AuthLevel.FINANCIAL, s.PaymentOutputFinancialList),
            (auth.AuthLevel.INITIATIVE_OWNER, s.PaymentOutputInitiatitveOwnerList),
            (auth.AuthLevel.GUEST, s.PaymentOutputGuestList),
        ],
        auth_levels=auth_levels,
        seq_key="payments",
    )
    return parsed_payments


# DEBIT CARD
@router.post(
    "/debit-card",
    response_model=le.DebitCardOutputActivityOwnerWithLinkedEntities,
    responses={
        404: {"description": "Initiative not found"},
        400: {"description": "A Debit Card with this card number already exists"},
    },
)
async def create_debit_card(
    debit_card: s.DebitCardCreateAdmin,
    requires_admin=Depends(auth.requires_admin),
    session: Session = Depends(get_session),
):
    initiative_db = session.get(ent.Initiative, debit_card.initiative_id)
    if not initiative_db:
        raise HTTPException(status_code=404, detail="Initiative not found")

    fields = get_fields_dict(debit_card.dict())
    new_debit_card = ent.DebitCard(initiative_id=debit_card.initiative_id, **fields)
    try:
        session.add(new_debit_card)
        session.commit()
        session.refresh(new_debit_card)
        return new_debit_card
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"A debit Card with card number {debit_card.card_number} already exists.",
        )


@router.patch(
    "/debit-card/{debit_card_id}",
    response_model=le.DebitCardOutputActivityOwnerWithLinkedEntities,
)
async def update_initiative_debit_card(
    debit_card_id: int,
    debit_card: s.DebitCardUpdateAdmin,
    requires_admin=Depends(auth.requires_admin),
    session: Session = Depends(get_session),
):
    initiative_db = session.get(ent.Initiative, debit_card.initiative_id)
    debit_card_db = session.get(ent.Activity, debit_card_id)

    if (
        not initiative_db
        or not debit_card_db
        or debit_card_db not in initiative_db.debit_cards
    ):
        raise HTTPException(
            status_code=404, detail="Initiative or Debit Card not found"
        )

    fields = get_fields_dict(debit_card.dict(exclude_unset=True))
    for key, value in fields.items():
        setattr(debit_card_db, key, value)

    session.add(debit_card_db)
    session.commit()
    session.refresh(debit_card_db)
    return debit_card_db


@router.get(
    "/initiative/{initiative_id}/debit-cards",
    response_model=s.DebitCardOutputActivityOwnerList,
)
async def get_initiative_debit_cards(
    initiative_id: int,
    requires_activity_owner=Depends(auth.requires_activity_owner),
    session: Session = Depends(get_session),
):
    initiative = session.get(ent.Initiative, initiative_id)
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")

    debit_cards = session.exec(
        select(ent.DebitCard).where(ent.DebitCard.initiative_id == initiative_id)
    ).all()
    return {"debit_cards": debit_cards}


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
    new_user = ent.User(**fields, hashed_password=auth.PWD_CONTEXT.hash(temp_password))
    if user.initiative_ids is not None:
        new_user.initiatives = get_entities_by_ids(
            session, ent.Initiative, user.initiative_ids
        )
    if user.activity_ids is not None:
        new_user.activities = get_entities_by_ids(
            session, ent.Activity, user.activity_ids
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
    session: Session = Depends(get_session),
    auth_levels: list[auth.AuthLevel] = Depends(
        auth.get_user_auth_levels(requires_login=True)
    ),
):
    user_db = session.get(ent.User, user_id)
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
            session, ent.Initiative, user.initiative_ids
        )
    if user.activity_ids is not None:
        user_db.activities = get_entities_by_ids(
            session, ent.Activity, user.activity_ids
        )
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
    # TODO: Make soft delete.
    user = session.get(ent.User, user_id)
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
    auth_levels: list[auth.AuthLevel] = Depends(
        auth.get_user_auth_levels(requires_login=True)
    ),
):
    # TODO: Enable searching by email.
    # TODO: pagination.
    users = session.exec(select(ent.User)).all()
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


# # BNG
@router.get(
    "/users/{user_id}/bng-initiate",
    response_class=RedirectResponse,
)
async def bng_initiate(
    user_id: int,
    bng: s.BNGCreateAdmin,
    requires_user_owner=Depends(auth.requires_user_owner),
    requires_admin=Depends(auth.requires_admin),
    session: Session = Depends(get_session),
    requester_ip: str = Depends(get_requester_ip),
):
    user = session.get(ent.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_bng = session.exec(select(ent.BNG)).first()
    if existing_bng:
        raise HTTPException(
            status_code=400,
            detail=f"A BNG Account with IBAN {existing_bng.iban} is already linked.",
        )
    try:
        consent_id, oauth_url = create_consent(
            iban=bng.iban,
            valid_until=bng.expires_on,
            redirect_url=f"https://{DOMAIN_NAME}/users/{user_id}/bng-callback",
            requester_ip=requester_ip,
        )
    except RequestException as e:
        raise HTTPException(
            status_code=500, detail="Error in request for consent to BNG."
        )
    token = jwt.encode(
        {
            "user_id": user_id,
            "iban": bng.iban,
            "bank_name": "BNG",
            "exp": time() + 1800,
            "consent_id": consent_id,
        },
        auth.SECRET_KEY,
        auth.ALGORITHM,
    ).decode("utf-8")
    url_to_return = oauth_url.format(token)
    # TODO: Don't return a redirect, but some json with the link.
    return RedirectResponse(url=url_to_return)


@router.post("/users/{user_id}/bng-callback", response_model=s.BNGOutputAdmin)
async def bng_callback(
    user_id: int,
    background_tasks: BackgroundTasks,
    code: str = Query(),
    state: str = Query(),
    session: Session = Depends(get_session),
):
    try:
        payload = jwt.decode(state, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="JWT token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate JWT token")

    try:
        response = retrieve_access_token(code, redirect_url="")
    except RequestException as e:
        raise HTTPException(
            status_code=500, detail="Error in retrieval of access token from BNG"
        )

    access_token, expires_in = response["access_token"], response["expires_in"]
    expires_on = datetime.now(pytz.timezone("Europe/Amsterdam")) + timedelta(
        seconds=int(expires_in)
    )
    new_bng_account = ent.BNG(
        iban=payload["iban"],
        expires_on=expires_on,
        user_id=payload["user_id"],
        consent_id=payload["consent_id"],
        access_token=access_token,
        last_import_on=None,
    )
    session.add(new_bng_account)
    session.commit()
    session.refresh(new_bng_account)
    background_tasks.add_task(get_bng_payments, session)
    # Here we should redirect the user back to a route in the SPA.
    return new_bng_account


@router.delete("/users/{user_id}/bng-connection")
async def delete_bng_connection(
    user_id: int,
    requires_user_owner=Depends(auth.requires_user_owner),
    requires_admin=Depends(auth.requires_admin),
    session: Session = Depends(get_session),
):
    existing_bng = session.exec(select(ent.BNG)).first()
    if not existing_bng:
        raise HTTPException(status_code=404, detail="No BNG Account exists")
    if existing_bng.user_id != user_id:
        raise HTTPException(
            status_code=403, detail="A BNG Account can only be deleted by the creator"
        )

    # TODO: Delete consent through API as well.
    session.delete(existing_bng)
    session.commit()
    return Response(status_code=204)


@router.get("/bng-connection", response_model=s.BNGOutputAdmin)
async def get_bng_connection(
    session: Session = Depends(get_session),
    auth_levels: list[auth.AuthLevel] = Depends(
        auth.get_user_auth_levels(requires_login=True)
    ),
):
    existing_bng = session.exec(select(ent.BNG)).first()
    if not existing_bng:
        raise HTTPException(status_code=404, detail="No BNG Account exists")

    parsed_bng = auth.validate_output_schema(
        existing_bng,
        parse_schemas=[
            (auth.AuthLevel.ADMIN, s.BNGOutputAdmin),
            (auth.AuthLevel.USER, s.BNGOutputUser),
        ],
        auth_levels=auth_levels,
    )
    return parsed_bng


# GOCARDLESS
@router.get("/users/{user_id}/gocardless-initiate", response_class=RedirectResponse)
async def gocardless_initiatite(
    user_id: int,
    # gocardless: s.GoCardlessCreateActivityOwnerCreate,
    logged_in_user=Depends(auth.get_logged_in_user),
    requires_user_owner=Depends(auth.requires_user_owner),
    session: Session = Depends(get_session),
):
    user = session.get(ent.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # A user can only have one requisition per bank (institution_id).
    # TODO

    await refresh_tokens()

    init = client.initialize_session(
        # TODO: This has to redirect to the SPA.
        redirect_uri=f"https://{DOMAIN_NAME}/users/{user_id}/gocardless-callback",
        # TODO: Parse dynamically
        institution_id="ING_INGBNL2A",
        reference_id=format_user_timestamp(user.id),
        max_historical_days=720,
    )

    new_requisition = ent.Requisition(
        user_id=user_id,
        api_institution_id="ING_INGBNL2A",
        api_requisition_id=init.requisition_id,
    )
    session.add(new_requisition)
    session.commit()
    # TODO: Don´t return a redirect, but some json with the link.
    return RedirectResponse(url=init.link)


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
