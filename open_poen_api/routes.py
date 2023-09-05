from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    BackgroundTasks,
    Query,
)
from typing import Optional
from fastapi.responses import RedirectResponse
from .database import get_async_session
from . import schemas as s
from . import models as ent
from . import managers as m
from .utils.utils import (
    temp_password_generator,
    get_requester_ip,
    format_user_timestamp,
)
import os
from .bng.api import create_consent
from .bng import import_bng_payments, retrieve_access_token, create_consent
from jose import jwt, JWTError, ExpiredSignatureError

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, and_
from requests import RequestException
from datetime import datetime, timedelta, date
from time import time
import pytz
from .authorization.authorization import SECRET_KEY, ALGORITHM
from .authorization import authorization as auth
from .gocardless import (
    refresh_tokens,
    client,
    INSTITUTION_ID_TO_TRANSACTION_TOTAL_DAYS,
    get_gocardless_payments,
)
import uuid


user_router = APIRouter(tags=["user"])
funder_router = APIRouter(tags=["funder"])
initiative_router = APIRouter(tags=["initiative"])
payment_router = APIRouter(tags=["payment"])


@user_router.post("/user", response_model=s.UserRead)
async def create_user(
    user: s.UserCreate,
    request: Request,
    superuser=Depends(m.superuser),
    user_manager: m.UserManager = Depends(m.UserManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    auth.authorize(superuser, "create", ent.User, oso)
    user_with_password = s.UserCreateWithPassword(
        **user.dict(), password=temp_password_generator(size=16)
    )
    user_db = await user_manager.create(user_with_password, request=request)
    return auth.get_authorized_output_fields(superuser, "read", user_db, oso)


@user_router.get(
    "/user/{user_id}",
    response_model=s.UserReadLinked,
    response_model_exclude_unset=True,
)
async def get_user(
    user_id: int,
    optional_user=Depends(m.optional_login),
    user_manager: m.UserManager = Depends(m.UserManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    user_db = await user_manager.detail_load(user_id)
    auth.authorize(optional_user, "read", user_db, oso)
    return auth.get_authorized_output_fields(optional_user, "read", user_db, oso)


@user_router.patch(
    "/user/{user_id}",
    response_model=s.UserRead,
    response_model_exclude_unset=True,
)
async def update_user(
    user_id: int,
    user: s.UserUpdate,
    request: Request,
    required_user=Depends(m.required_login),
    user_manager: m.UserManager = Depends(m.UserManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    user_db = await user_manager.min_load(user_id)
    auth.authorize(required_user, "edit", user_db, oso)
    auth.authorize_input_fields(required_user, "edit", user_db, user)
    edited_user = await user_manager.update(user, user_db, request=request)
    return auth.get_authorized_output_fields(required_user, "read", edited_user, oso)


@user_router.delete("/user/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    superuser=Depends(m.superuser),
    user_manager: m.UserManager = Depends(m.UserManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    user_db = await user_manager.min_load(user_id)
    auth.authorize(superuser, "delete", user_db, oso)
    await user_manager.delete(user_db, request=request)
    return Response(status_code=204)


@user_router.get(
    "/users", response_model=s.UserReadList, response_model_exclude_unset=True
)
async def get_users(
    session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(m.optional_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    # TODO: Enable searching by email.
    # TODO: pagination.
    q = auth.get_authorized_query(optional_user, "read", ent.User, oso)
    users_result = await session.execute(q)
    users_scalar = users_result.scalars().all()
    filtered_users = [
        auth.get_authorized_output_fields(optional_user, "read", i, oso)
        for i in users_scalar
    ]
    return s.UserReadList(users=filtered_users)


# BNG
@user_router.get(
    "/users/{user_id}/bng-initiate",
    response_model=s.BNGInitiate,
    summary="BNG Initiate",
)
async def bng_initiate(
    user_id: int,
    iban: str = Depends(s.validate_iban),
    expires_on: date = Depends(s.validate_expires_on),
    session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(m.optional_login),  # TODO
    requester_ip: str = Depends(get_requester_ip),
):
    user = await session.get(ent.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_bng_q = await session.execute(select(ent.BNG))
    existing_bng = existing_bng_q.scalars().first()
    if existing_bng:
        raise HTTPException(
            status_code=400,
            detail=f"A BNG Account with IBAN {existing_bng.iban} is already linked.",
        )
    try:
        consent_id, oauth_url = create_consent(
            iban=iban,
            valid_until=expires_on,
            redirect_url=f"https://{os.environ['DOMAIN_NAME']}/users/{user_id}/bng-callback",
            requester_ip=requester_ip,
        )
    except RequestException as e:
        raise HTTPException(
            status_code=500, detail="Error in request for consent to BNG."
        )
    token = jwt.encode(
        {
            "user_id": user_id,
            "iban": iban,
            "bank_name": "BNG",
            "exp": time() + 1800,
            "consent_id": consent_id,
        },
        SECRET_KEY,
        ALGORITHM,
    )
    url_to_return = oauth_url.format(token)
    return s.BNGInitiate(url=url_to_return)


@user_router.get("/users/{user_id}/bng-callback", include_in_schema=False)
async def bng_callback(
    user_id: int,
    background_tasks: BackgroundTasks,
    code: str = Query(),
    state: str = Query(),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        payload = jwt.decode(state, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="JWT token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate JWT token")

    try:
        response = retrieve_access_token(
            code,
            redirect_url=f"https://{os.environ.get('DOMAIN_NAME')}/users/{user_id}/bng-callback",
            requester_ip="",
        )
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
    await session.commit()
    # TODO: On first import, import the entire history.
    # background_tasks.add_task(get_bng_payments, session)  # TODO
    return RedirectResponse(url=os.environ["SPA_BNG_CALLBACK_REDIRECT_URL"])


# @user_router.delete("/users/{user_id}/bng-connection")
# async def delete_bng_connection(
#     user_id: int,
#     requires_user_owner=Depends(auth.requires_user_owner),
#     requires_admin=Depends(auth.requires_admin),
#     session: AsyncSession = Depends(get_async_session),
# ):
#     existing_bng = session.exec(select(ent.BNG)).first()
#     if not existing_bng:
#         raise HTTPException(status_code=404, detail="No BNG Account exists")
#     if existing_bng.user_id != user_id:
#         raise HTTPException(
#             status_code=403, detail="A BNG Account can only be deleted by the creator"
#         )

#     # TODO: Delete consent through API as well.
#     session.delete(existing_bng)
#     session.commit()
#     return Response(status_code=204)


# GOCARDLESS
@user_router.get(
    "/users/{user_id}/gocardless-initiate",
    response_model=s.GocardlessInitiate,
    summary="GoCardless Initiate",
)
async def gocardless_initiatite(
    user_id: int,
    institution_id: str = Depends(s.validate_institution_id),
    n_days_access: int = Depends(s.validate_n_days_access),
    n_days_history: int = Depends(s.validate_n_days_history),
    session: AsyncSession = Depends(get_async_session),
    required_user=Depends(m.required_login),
    user_manager: m.UserManager = Depends(m.UserManager),
):
    user = await user_manager.min_load(user_id)

    await refresh_tokens()

    reference_id = str(uuid.uuid4())

    token = jwt.encode(
        {
            "user_id": user_id,
            "reference_id": reference_id,
            "exp": time() + 1800,
        },
        SECRET_KEY,
        ALGORITHM,
    )

    init = client.initialize_session(
        redirect_uri=f"https://{os.environ.get('DOMAIN_NAME')}/users/{user_id}/gocardless-callback",
        institution_id=institution_id,
        reference_id=token,
        max_historical_days=n_days_history,
        access_valid_for_days=n_days_access,
    )

    requisition_db = ent.Requisition(
        user_id=user_id,
        institution_id=institution_id,
        api_requisition_id=init.requisition_id,
        reference_id=reference_id,
        status=ent.ReqStatus.CREATED,
        n_days_history=n_days_history,
        n_days_access=n_days_access,
    )
    session.add(requisition_db)
    await session.commit()

    return s.GocardlessInitiate(url=init.link)


@user_router.get("/users/{user_id}/gocardless-callback", include_in_schema=False)
async def gocardless_callback(
    user_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    ref: str,
    error: str | None = None,
    details: str | None = None,
    session: AsyncSession = Depends(get_async_session),
):
    if error is not None:
        raise HTTPException(status_code=500, detail=details)

    try:
        payload = jwt.decode(ref, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="JWT token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate JWT token")

    if payload["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="User not found")

    requisition_q = await session.execute(
        select(ent.Requisition).where(
            and_(
                ent.Requisition.reference_id == payload["reference_id"],
                ent.Requisition.user_id == payload["user_id"],
            )
        )
    )
    requisition = requisition_q.scalars().first()
    if requisition is None:
        raise HTTPException(status_code=404, detail="Requisition not found")

    requisition.callback_handled = True
    session.add(requisition)
    await session.commit()

    background_tasks.add_task(
        get_gocardless_payments,
        requisition.id,
        datetime.today() - timedelta(days=requisition.n_days_history + 1),
    )
    return RedirectResponse(url=os.environ["SPA_GOCARDLESS_CALLBACK_REDIRECT_URL"])


@user_router.get(
    "/user/{user_id}/bank_account/{bank_account_id}",
    response_model=s.BankAccountReadLinked,
    response_model_exclude_unset=True,
)
async def get_bank_account(
    user_id: int,
    bank_account_id: int,
    required_user=Depends(m.required_login),
    bank_account_manager: m.BankAccountManager = Depends(m.BankAccountManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    bank_account_db = await bank_account_manager.detail_load(bank_account_id)
    auth.authorize(required_user, "read", bank_account_db, oso)
    return auth.get_authorized_output_fields(
        required_user, "read", bank_account_db, oso
    )


@user_router.patch(
    "/user/{user_id}/bank_account/{bank_account_id}",
    response_model=s.BankAccountRead,
)
async def finish_bank_account(
    user_id: int,
    bank_account_id: int,
    request: Request,
    required_user=Depends(m.required_login),
    bank_account_manager: m.BankAccountManager = Depends(m.BankAccountManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    bank_account_db = await bank_account_manager.detail_load(bank_account_id)
    auth.authorize(required_user, "finish", bank_account_db, oso)
    bank_account_db = await bank_account_manager.finish(
        bank_account_db, request=request
    )
    return bank_account_db


@user_router.delete("/user/{user_id}/bank_account/{bank_account_id}")
async def delete_bank_account(
    user_id: int,
    bank_account_id: int,
    request: Request,
    required_user=Depends(m.required_login),
    bank_account_manager: m.BankAccountManager = Depends(m.BankAccountManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    bank_account_db = await bank_account_manager.detail_load(bank_account_id)
    auth.authorize(required_user, "delete", bank_account_db, oso)
    await bank_account_manager.delete(bank_account_db, request=request)
    return Response(status_code=204)


@user_router.patch(
    "/user/{user_id}/bank_account/{bank_account_id}/users",
    response_model=s.UserReadList,
)
async def link_bank_account_users(
    user_id: int,
    bank_account_id: int,
    bank_account: s.BankAccountUsersUpdate,
    request: Request,
    required_user=Depends(m.required_login),
    bank_account_manager: m.BankAccountManager = Depends(m.BankAccountManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    bank_account_db = await bank_account_manager.detail_load(bank_account_id)
    auth.authorize(required_user, "link_users", bank_account_db, oso)
    bank_account_db = await bank_account_manager.make_users_user(
        bank_account_db, bank_account.user_ids, request=request
    )
    # Important for up to date relations. Has to be in this async context.
    await bank_account_manager.session.refresh(bank_account_db)
    filtered_bank_account_users = [
        auth.get_authorized_output_fields(
            required_user, "read", i, oso, ent.User.REL_FIELDS
        )
        for i in bank_account_db.users
    ]
    return s.UserReadList(users=filtered_bank_account_users)


@initiative_router.get(
    "/initiative/{initiative_id}",
    response_model=s.InitiativeReadLinked,
    response_model_exclude_unset=True,
)
async def get_initiative(
    initiative_id: int,
    optional_user=Depends(m.optional_login),
    initiative_manager: m.InitiativeManager = Depends(m.InitiativeManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    initiative_db = await initiative_manager.detail_load(initiative_id)
    auth.authorize(optional_user, "read", initiative_db, oso)
    return auth.get_authorized_output_fields(optional_user, "read", initiative_db, oso)


@initiative_router.patch(
    "/initiative/{initiative_id}",
    response_model=s.InitiativeRead,
    response_model_exclude_unset=True,
)
async def update_initiative(
    initiative_id: int,
    initiative: s.InitiativeUpdate,
    request: Request,
    required_user=Depends(m.required_login),
    initiative_manager: m.InitiativeManager = Depends(m.InitiativeManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    initiative_db = await initiative_manager.min_load(initiative_id)
    auth.authorize(required_user, "edit", initiative_db, oso)
    auth.authorize_input_fields(required_user, "edit", initiative_db, initiative)
    edited_initiative = await initiative_manager.update(
        initiative, initiative_db, request=request
    )
    return auth.get_authorized_output_fields(
        required_user, "read", edited_initiative, oso
    )


@initiative_router.patch(
    "/initiative/{initiative_id}/owners",
    response_model=s.UserReadList,
)
async def link_initiative_owners(
    initiative_id: int,
    initiative: s.InitiativeOwnersUpdate,
    request: Request,
    required_user=Depends(m.required_login),
    initiative_manager: m.InitiativeManager = Depends(m.InitiativeManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    initiative_db = await initiative_manager.detail_load(initiative_id)
    auth.authorize(required_user, "edit", initiative_db, oso)
    initiative_db = await initiative_manager.make_users_owner(
        initiative_db, initiative.user_ids, request=request
    )
    # Important for up to date relations. Has to be in this async context.
    await initiative_manager.session.refresh(initiative_db)
    filtered_initiative_owners = [
        auth.get_authorized_output_fields(
            required_user, "read", i, oso, ent.User.REL_FIELDS
        )
        for i in initiative_db.initiative_owners
    ]
    return s.UserReadList(users=filtered_initiative_owners)


@initiative_router.delete("/initiative/{initiative_id}")
async def delete_initiative(
    initiative_id: int,
    request: Request,
    required_user=Depends(m.required_login),
    initiative_manager: m.InitiativeManager = Depends(m.InitiativeManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    initiative_db = await initiative_manager.min_load(initiative_id)
    auth.authorize(required_user, "delete", initiative_db, oso)
    await initiative_manager.delete(initiative_db, request=request)
    return Response(status_code=204)


@initiative_router.get(
    "/initiatives",
    response_model=s.InitiativeReadList,
    response_model_exclude_unset=True,
)
async def get_initiatives(
    async_session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(m.optional_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    # TODO: pagination.
    q = auth.get_authorized_query(optional_user, "read", ent.Initiative, oso)
    initiatives_result = await async_session.execute(q)
    initiatives_scalar = initiatives_result.scalars().all()
    # TODO: This part is resulting in a lot of extra separate queries for authorization.
    # Check if this goes away if we join load the neccessary relationships.
    filtered_initiatives = [
        auth.get_authorized_output_fields(optional_user, "read", i, oso)
        for i in initiatives_scalar
    ]
    return s.InitiativeReadList(initiatives=filtered_initiatives)


@initiative_router.post(
    "/initiative/{initiative_id}/activity", response_model=s.ActivityRead
)
async def create_activity(
    initiative_id: int,
    activity: s.ActivityCreate,
    request: Request,
    required_user=Depends(m.required_login),
    initiative_manager: m.InitiativeManager = Depends(m.InitiativeManager),
    activity_manager: m.ActivityManager = Depends(m.ActivityManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    initiative_db = await initiative_manager.min_load(initiative_id)
    auth.authorize(required_user, "create_activity", initiative_db, oso)
    activity_db = await activity_manager.create(
        activity, initiative_id, request=request
    )
    return auth.get_authorized_output_fields(required_user, "read", activity_db, oso)


@initiative_router.get(
    "/initiative/{initiative_id}/activity/{activity_id}",
    response_model=s.ActivityReadLinked,
    response_model_exclude_unset=True,
)
async def get_activity(
    initiative_id: int,
    activity_id: int,
    optional_user=Depends(m.optional_login),
    activity_manager: m.ActivityManager = Depends(m.ActivityManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    activity_db = await activity_manager.detail_load(initiative_id, activity_id)
    auth.authorize(optional_user, "read", activity_db, oso)
    return auth.get_authorized_output_fields(optional_user, "read", activity_db, oso)


@initiative_router.patch(
    "/initiative/{initiative_id}/activity/{activity_id}",
    response_model=s.ActivityRead,
    response_model_exclude_unset=True,
)
async def update_activity(
    initiative_id: int,
    activity_id: int,
    activity: s.ActivityUpdate,
    request: Request,
    required_user=Depends(m.required_login),
    activity_manager: m.ActivityManager = Depends(m.ActivityManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    activity_db = await activity_manager.min_load(initiative_id, activity_id)
    auth.authorize(required_user, "edit", activity_db, oso)
    auth.authorize_input_fields(required_user, "edit", activity_db, activity)
    edited_activity = await activity_manager.update(
        activity, activity_db, request=request
    )
    return auth.get_authorized_output_fields(
        required_user, "read", edited_activity, oso
    )


@initiative_router.patch(
    "/initiative/{initiative_id}/activity/{activity_id}/owners",
    response_model=s.UserReadList,
)
async def link_activity_owners(
    initiative_id: int,
    activity_id: int,
    activity: s.ActivityOwnersUpdate,
    request: Request,
    required_user=Depends(m.required_login),
    activity_manager: m.ActivityManager = Depends(m.ActivityManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    activity_db = await activity_manager.detail_load(initiative_id, activity_id)
    auth.authorize(required_user, "link_owners", activity_db, oso)
    activity_db = await activity_manager.make_users_owner(
        activity_db, activity.user_ids, request=request
    )
    # Important for up to date relations. Has to be in this async context.
    await activity_manager.session.refresh(activity_db)
    filtered_activity_owners = [
        auth.get_authorized_output_fields(
            required_user, "read", i, oso, ent.User.REL_FIELDS
        )
        for i in activity_db.activity_owners
    ]
    return s.UserReadList(users=filtered_activity_owners)


@initiative_router.delete("/initiative/{initiative_id}/activity/{activity_id}")
async def delete_activity(
    initiative_id: int,
    activity_id: int,
    request: Request,
    required_user=Depends(m.required_login),
    activity_manager: m.ActivityManager = Depends(m.ActivityManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    activity_db = await activity_manager.min_load(initiative_id, activity_id)
    auth.authorize(required_user, "delete", activity_db, oso)
    await activity_manager.delete(activity_db, request=request)
    return Response(status_code=204)


@initiative_router.patch(
    "/initiative/{initiative_id}/debit-cards",
    response_model=s.DebitCardReadList,
)
async def link_initiative_debit_cards(
    initiative_id: int,
    initiative: s.InitiativeDebitCardsUpdate,
    request: Request,
    required_user=Depends(m.required_login),
    initiative_manager: m.InitiativeManager = Depends(m.InitiativeManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    initiative_db = await initiative_manager.detail_load(initiative_id)
    auth.authorize(required_user, "link_cards", initiative_db, oso)
    initiative_db = await initiative_manager.link_debit_cards(
        initiative_db,
        initiative.card_numbers,
        request=request,
        ignore_already_linked=initiative.ignore_already_linked,
    )
    # Important for up to date relations. Has to be in this async context.
    await initiative_manager.session.refresh(initiative_db)
    filtered_debit_cards = [
        auth.get_authorized_output_fields(required_user, "read", i, oso)
        for i in initiative_db.debit_cards
    ]
    return s.DebitCardReadList(debit_cards=filtered_debit_cards)


@funder_router.post("/funder", response_model=s.FunderRead)
async def create_funder(
    funder: s.FunderCreate,
    request: Request,
    required_user=Depends(m.required_login),
    funder_manager: m.FunderManager = Depends(m.FunderManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    auth.authorize(required_user, "create", "Funder", oso)
    funder_db = await funder_manager.create(funder, request=request)
    return auth.get_authorized_output_fields(required_user, "read", funder_db, oso)


@funder_router.get(
    "/funder/{funder_id}",
    response_model=s.FunderReadLinked,
    response_model_exclude_unset=True,
)
async def get_funder(
    funder_id: int,
    optional_user=Depends(m.optional_login),
    funder_manager: m.FunderManager = Depends(m.FunderManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    funder_db = await funder_manager.detail_load(funder_id)
    auth.authorize(optional_user, "read", funder_db, oso)
    return auth.get_authorized_output_fields(optional_user, "read", funder_db, oso)


@funder_router.patch(
    "/funder/{funder_id}",
    response_model=s.FunderRead,
    response_model_exclude_unset=True,
)
async def update_funder(
    funder_id: int,
    funder: s.FunderUpdate,
    request: Request,
    required_user=Depends(m.required_login),
    funder_manager: m.FunderManager = Depends(m.FunderManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    funder_db = await funder_manager.min_load(funder_id)
    auth.authorize(required_user, "edit", funder_db, oso)
    auth.authorize_input_fields(required_user, "edit", funder_db, funder)
    edited_funder = await funder_manager.update(funder, funder_db, request=request)
    return auth.get_authorized_output_fields(required_user, "read", edited_funder, oso)


@funder_router.delete("/funder/{funder_id}")
async def delete_funder(
    funder_id: int,
    request: Request,
    required_user=Depends(m.required_login),
    funder_manager: m.FunderManager = Depends(m.FunderManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    funder_db = await funder_manager.min_load(funder_id)
    auth.authorize(required_user, "delete", funder_db, oso)
    await funder_manager.delete(funder_db, request=request)
    return Response(status_code=204)


@funder_router.get(
    "/funders",
    response_model=s.FunderReadList,
    response_model_exclude_unset=True,
)
async def get_funders(
    async_session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(m.optional_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    # TODO: pagination.
    q = auth.get_authorized_query(optional_user, "read", ent.Funder, oso)
    funders_result = await async_session.execute(q)
    funders_scalar = funders_result.scalars().all()
    filtered_funders = [
        auth.get_authorized_output_fields(optional_user, "read", i, oso)
        for i in funders_scalar
    ]
    return s.FunderReadList(funders=filtered_funders)


@funder_router.post("/funder/{funder_id}/regulation", response_model=s.RegulationRead)
async def create_regulation(
    funder_id: int,
    regulation: s.RegulationCreate,
    request: Request,
    required_user=Depends(m.required_login),
    funder_manager: m.FunderManager = Depends(m.FunderManager),
    regulation_manager: m.RegulationManager = Depends(m.RegulationManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    funder_db = await funder_manager.min_load(funder_id)
    auth.authorize(required_user, "create", "Regulation", oso)
    regulation_db = await regulation_manager.create(
        regulation, funder_id, request=request
    )
    return auth.get_authorized_output_fields(required_user, "read", regulation_db, oso)


@funder_router.get(
    "/funder/{funder_id}/regulation/{regulation_id}",
    response_model=s.RegulationReadLinked,
    response_model_exclude_unset=True,
)
async def get_regulation(
    funder_id: int,
    regulation_id: int,
    optional_user=Depends(m.optional_login),
    regulation_manager: m.RegulationManager = Depends(m.RegulationManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    regulation_db = await regulation_manager.detail_load(regulation_id)
    auth.authorize(optional_user, "read", regulation_db, oso)
    return auth.get_authorized_output_fields(optional_user, "read", regulation_db, oso)


@funder_router.patch(
    "/funder/{funder_id}/regulation/{regulation_id}",
    response_model=s.RegulationRead,
    response_model_exclude_unset=True,
)
async def update_regulation(
    funder_id: int,
    regulation_id: int,
    regulation: s.RegulationUpdate,
    request: Request,
    required_user=Depends(m.required_login),
    regulation_manager: m.RegulationManager = Depends(m.RegulationManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    regulation_db = await regulation_manager.min_load(regulation_id)
    auth.authorize(required_user, "edit", regulation_db, oso)
    auth.authorize_input_fields(required_user, "edit", regulation_db, regulation)
    edited_regulation = await regulation_manager.update(
        regulation, regulation_db, request=request
    )
    return auth.get_authorized_output_fields(
        required_user, "read", edited_regulation, oso
    )


@funder_router.patch(
    "/funder/{funder_id}/regulation/{regulation_id}/officers",
    response_model=s.UserReadList,
)
async def link_officers(
    funder_id: int,
    regulation_id: int,
    regulation: s.RegulationOfficersUpdate,
    request: Request,
    required_user=Depends(m.required_login),
    regulation_manager: m.RegulationManager = Depends(m.RegulationManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    regulation_db = await regulation_manager.detail_load(regulation_id)
    auth.authorize(required_user, "edit", regulation_db, oso)
    regulation_db = await regulation_manager.make_users_officer(
        regulation_db,
        regulation.user_ids,
        regulation_role=regulation.role,
        request=request,
    )
    # Important for up to date relations. Has to be in this async context.
    await regulation_manager.session.refresh(regulation_db)

    officers = (
        regulation_db.grant_officers
        if regulation.role == ent.RegulationRole.GRANT_OFFICER
        else regulation_db.policy_officers
    )
    filtered_officers = [
        auth.get_authorized_output_fields(
            required_user, "read", i, oso, ent.User.REL_FIELDS
        )
        for i in officers
    ]
    return s.UserReadList(users=filtered_officers)


@funder_router.delete("/funder/{funder_id}/regulation/{regulation_id}")
async def delete_regulation(
    funder_id: int,
    regulation_id: int,
    request: Request,
    required_user=Depends(m.required_login),
    regulation_manager: m.RegulationManager = Depends(m.RegulationManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    regulation_db = await regulation_manager.min_load(regulation_id)
    auth.authorize(required_user, "delete", regulation_db, oso)
    await regulation_manager.delete(regulation_db, request=request)
    return Response(status_code=204)


@funder_router.get(
    "/funder/{funder_id}/regulations",
    response_model=s.RegulationReadList,
    response_model_exclude_unset=True,
)
async def get_regulations(
    funder_id: int,
    async_session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(m.optional_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    # TODO: pagination.
    q = auth.get_authorized_query(optional_user, "read", ent.Regulation, oso)
    q = q.where(ent.Regulation.funder_id == funder_id)
    regulations_result = await async_session.execute(q)
    regulations_scalar = regulations_result.scalars().all()
    filtered_regulations = [
        auth.get_authorized_output_fields(optional_user, "read", i, oso)
        for i in regulations_scalar
    ]
    return s.RegulationReadList(regulations=filtered_regulations)


@funder_router.post(
    "/funder/{funder_id}/regulation/{regulation_id}/grant", response_model=s.GrantRead
)
async def create_grant(
    funder_id: int,
    regulation_id: int,
    grant: s.GrantCreate,
    request: Request,
    required_user=Depends(m.required_login),
    regulation_manager: m.RegulationManager = Depends(m.RegulationManager),
    grant_manager: m.GrantManager = Depends(m.GrantManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    # TODO: What to do with funder_id?
    regulation_db = await regulation_manager.min_load(regulation_id)
    auth.authorize(required_user, "create_grant", regulation_db, oso)
    grant_db = await grant_manager.create(grant, regulation_id, request=request)
    return auth.get_authorized_output_fields(required_user, "read", grant_db, oso)


@funder_router.get(
    "/funder/{funder_id}/regulation/{regulation_id}/grant/{grant_id}",
    response_model=s.GrantReadLinked,
    response_model_exclude_unset=True,
)
async def get_grant(
    funder_id: int,
    regulation_id: int,
    grant_id: int,
    optional_user=Depends(m.optional_login),
    grant_manager: m.GrantManager = Depends(m.GrantManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    grant_db = await grant_manager.detail_load(grant_id)
    auth.authorize(optional_user, "read", grant_db, oso)
    return auth.get_authorized_output_fields(optional_user, "read", grant_db, oso)


@funder_router.patch(
    "/funder/{funder_id}/regulation/{regulation_id}/grant/{grant_id}",
    response_model=s.GrantRead,
    response_model_exclude_unset=True,
)
async def update_grant(
    funder_id: int,
    regulation_id: int,
    grant_id: int,
    grant: s.GrantUpdate,
    request: Request,
    required_user=Depends(m.required_login),
    grant_manager: m.GrantManager = Depends(m.GrantManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    grant_db = await grant_manager.min_load(grant_id)
    auth.authorize(required_user, "edit", grant_db, oso)
    auth.authorize_input_fields(required_user, "edit", grant_db, grant)
    edited_grant = await grant_manager.update(grant, grant_db, request=request)
    return auth.get_authorized_output_fields(required_user, "read", edited_grant, oso)


@funder_router.patch(
    "/funder/{funder_id}/regulation/{regulation_id}/grant/{grant_id}/overseer",
    response_model=s.UserReadList,
    responses={204: {"description": "Grant overseer is removed"}},
)
async def link_overseer(
    funder_id: int,
    regulation_id: int,
    grant_id: int,
    grant: s.GrantOverseerUpdate,
    request: Request,
    required_user=Depends(m.required_login),
    grant_manager: m.GrantManager = Depends(m.GrantManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    grant_db = await grant_manager.detail_load(grant_id)
    auth.authorize(required_user, "edit", grant_db, oso)
    grant_db = await grant_manager.make_users_overseer(
        grant_db, grant.user_ids, request=request
    )
    # Important for up to date relations. Has to be in this async context.
    await grant_manager.session.refresh(grant_db)
    filtered_overseers = [
        auth.get_authorized_output_fields(
            required_user, "read", i, oso, ent.User.REL_FIELDS
        )
        for i in grant_db.overseers
    ]
    return s.UserReadList(users=filtered_overseers)


@funder_router.delete("/funder/{funder_id}/regulation/{regulation_id}/grant/{grant_id}")
async def delete_grant(
    funder_id: int,
    regulation_id: int,
    grant_id: int,
    request: Request,
    required_user=Depends(m.required_login),
    grant_manager: m.GrantManager = Depends(m.GrantManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    grant_db = await grant_manager.min_load(grant_id)
    auth.authorize(required_user, "delete", grant_db, oso)
    await grant_manager.delete(grant_db, request=request)
    return Response(status_code=204)


@funder_router.get(
    "/funder/{funder_id}/regulation/{regulation_id}/grants",
    response_model=s.GrantReadList,
    response_model_exclude_unset=True,
)
async def get_grants(
    funder_id: int,
    regulation_id: int,
    async_session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(m.optional_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    q = auth.get_authorized_query(optional_user, "read", ent.Grant, oso)
    q = q.where(ent.Grant.regulation_id == regulation_id)
    grants_result = await async_session.execute(q)
    grants_scalar = grants_result.scalars().all()
    filtered_grants = [
        auth.get_authorized_output_fields(optional_user, "read", i, oso)
        for i in grants_scalar
    ]
    return s.GrantReadList(grants=filtered_grants)


@funder_router.post(
    "/funder/{funder_id}/regulation/{regulation_id}/grant/{grant_id}/initiative",
    response_model=s.InitiativeRead,
)
async def create_initiative(
    funder_id: int,
    regulation_id: int,
    grant_id: int,
    initiative: s.InitiativeCreate,
    request: Request,
    required_user=Depends(m.required_login),
    grant_manager: m.GrantManager = Depends(m.GrantManager),
    initiative_manager: m.InitiativeManager = Depends(m.InitiativeManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    grant_db = await grant_manager.min_load(grant_id)
    auth.authorize(required_user, "create_initiative", grant_db, oso)
    # TODO: Validate funder_id, regulation_id and grant_id.
    initiative_db = await initiative_manager.create(
        initiative, grant_id, request=request
    )
    return auth.get_authorized_output_fields(required_user, "read", initiative_db, oso)


@payment_router.post(
    "/payment",
    response_model=s.PaymentRead,
)
async def create_payment(
    payment: s.PaymentCreateManual,
    request: Request,
    required_user=Depends(m.required_login),
    payment_manager: m.PaymentManager = Depends(m.PaymentManager),
    initiative_manager: m.InitiativeManager = Depends(m.InitiativeManager),
    activity_manager: m.ActivityManager = Depends(m.ActivityManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    if payment.activity_id is not None:
        activity_db = await activity_manager.min_load(
            payment.initiative_id, payment.activity_id
        )
        auth.authorize(required_user, "create_payment", activity_db, oso)
    else:
        initiative_db = await initiative_manager.min_load(payment.initiative_id)
        auth.authorize(required_user, "create_payment", initiative_db, oso)

    payment_db = await payment_manager.create(
        payment, payment.initiative_id, payment.activity_id, request=request
    )
    return auth.get_authorized_output_fields(required_user, "read", payment_db, oso)


@payment_router.patch(
    "/payment/{payment_id}",
    response_model=s.PaymentRead,
    response_model_exclude_unset=True,
)
async def update_payment(
    payment_id: int,
    payment: s.PaymentUpdate,
    request: Request,
    required_user=Depends(m.required_login),
    payment_manager: m.PaymentManager = Depends(m.PaymentManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    payment_db = await payment_manager.min_load(payment_id)
    auth.authorize(required_user, "edit", payment_db, oso)
    auth.authorize_input_fields(required_user, "edit", payment_db, payment)
    edited_payment = await payment_manager.update(payment, payment_db, request=request)
    return auth.get_authorized_output_fields(required_user, "read", edited_payment, oso)


@payment_router.patch(
    "/payment/{payment_id}/initiative",
    response_model=s.PaymentRead,
)
async def link_initiative(
    payment_id: int,
    payment: s.PaymentInitiativeUpdate,
    request: Request,
    required_user=Depends(m.required_login),
    payment_manager: m.PaymentManager = Depends(m.PaymentManager),
    initiative_manager: m.InitiativeManager = Depends(m.InitiativeManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    payment_db = await payment_manager.detail_load(payment_id)
    if payment_db.activity_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Payment is still linked to an activity. First decouple it.",
        )
    auth.authorize(required_user, "link_initiative", payment_db, oso)

    if payment.initiative_id is not None:
        initiative_db = await initiative_manager.detail_load(payment.initiative_id)
        auth.authorize(required_user, "link_payment", initiative_db, oso)

    payment_db = await payment_manager.assign_payment_to_initiative(
        payment_db,
        payment.initiative_id,
        request=request,
    )
    # Important for up to date relations. Has to be in this async context.
    await payment_manager.session.refresh(payment_db)
    return auth.get_authorized_output_fields(required_user, "read", payment_db, oso)


@payment_router.patch(
    "/payment/{payment_id}/activity",
    response_model=s.PaymentRead,
)
async def link_activity(
    payment_id: int,
    payment: s.PaymentActivityUpdate,
    request: Request,
    required_user=Depends(m.required_login),
    payment_manager: m.PaymentManager = Depends(m.PaymentManager),
    activity_manager: m.ActivityManager = Depends(m.ActivityManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    payment_db = await payment_manager.detail_load(payment_id)
    if payment_db.initiative_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Payment is not linked to an initiative. First couple it.",
        )
    auth.authorize(required_user, "link_activity", payment_db, oso)

    if payment.activity_id is not None:
        activity_db = await activity_manager.detail_load(
            payment.initiative_id, payment.activity_id
        )
        auth.authorize(required_user, "link_payment", activity_db, oso)

    payment_db = await payment_manager.assign_payment_to_activity(
        payment_db, payment.activity_id, request=request
    )
    # Important for up to date relations. Has to be in this async context.
    await payment_manager.session.refresh(payment_db)
    return auth.get_authorized_output_fields(required_user, "read", payment_db, oso)


@payment_router.delete("/payment/{payment_id}")
async def delete_payment(
    payment_id: int,
    request: Request,
    required_user=Depends(m.required_login),
    payment_manager: m.PaymentManager = Depends(m.PaymentManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    payment_db = await payment_manager.min_load(payment_id)
    auth.authorize(required_user, "delete", payment_db, oso)
    await payment_manager.delete(payment_db, request=request)
    return Response(status_code=204)


@payment_router.get(
    "/payments/bng",
    response_model=s.PaymentReadList,
    response_model_exclude_unset=True,
    summary="Get BNG Payments",
)
async def get_bng_payments(
    async_session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(m.optional_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    pass


@payment_router.get(
    "/payments/user/{user_id}",
    response_model=s.PaymentReadList,
    response_model_exclude_unset=True,
)
async def get_user_payments(
    user_id: int,
    async_session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(m.optional_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    pass


@payment_router.get(
    "/payments/initiative/{initiative_id}",
    response_model=s.PaymentReadList,
    response_model_exclude_unset=True,
)
async def get_initiative_payments(
    initiative_id: int,
    async_session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(m.optional_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    pass


@payment_router.get(
    "/payments/initiative/{initiative_id}/activity/{activity_id}",
    response_model=s.PaymentReadList,
    response_model_exclude_unset=True,
)
async def get_activity_payments(
    initiative_id: int,
    activity_id: int,
    async_session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(m.optional_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    pass
