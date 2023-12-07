from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    BackgroundTasks,
    Query,
    UploadFile,
    File,
    Body,
    Path,
)
from typing import Annotated, Union
from fastapi.responses import RedirectResponse
from .database import get_async_session
from . import schemas as s
from . import models as ent
from . import managers as m
from .utils.utils import (
    temp_password_generator,
    get_requester_ip,
)
import os
from .bng.api import create_consent
from .bng import import_bng_payments, retrieve_access_token, create_consent
from jose import jwt, JWTError, ExpiredSignatureError

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from requests import RequestException
from datetime import datetime, timedelta, date
from time import time
import pytz
from .authorization.authorization import SECRET_KEY, ALGORITHM
from .authorization import authorization as auth
from .gocardless import (
    get_nordigen_client,
    get_gocardless_payments,
    GoCardlessInstitutionList,
)
from .gocardless import get_institutions as get_institutions_from_gocardless
from nordigen import NordigenClient
import uuid
from .exc import NotAuthorized, EntityNotFound
from .logger import audit_logger
from .query import (
    get_initiatives_q,
    get_users_q,
    get_funders_q,
    get_regulations_q,
    get_grants_q,
    get_user_payments_q,
    get_linkable_initiatives_q,
    get_linkable_activities_q,
    get_initiative_payments_q,
    get_activity_payments_q,
    get_initiative_media_q,
)

user_router = APIRouter(tags=["user"])
funder_router = APIRouter(tags=["funder"])
initiative_router = APIRouter(tags=["initiative"])
payment_router = APIRouter(tags=["payment"])
permission_router = APIRouter(tags=["auth"])
utils_router = APIRouter(tags=["utils"])


@user_router.post("/user", response_model=s.UserRead)
async def create_user(
    user: Annotated[
        s.UserCreate,
        Body(
            example={
                "email": "henkdevries@gmail.com",
                "role": "user",
                "is_superuser": True,
            }
        ),
    ],
    request: Request,
    required_login=Depends(m.required_login),
    user_manager: m.UserManager = Depends(m.UserManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    auth.authorize(required_login, "create", "User", oso)
    user_with_password = s.UserCreateWithPassword(
        **user.dict(), password=temp_password_generator(size=16)
    )
    user_db = await user_manager.create(user_with_password, request=request)
    # TODO: Also see initiative. How to deal with this?
    await user_db.awaitable_attrs.profile_picture
    return auth.get_authorized_output_fields(required_login, "read", user_db, oso)


@user_router.get(
    "/user/{user_id}",
    response_model=s.UserReadLinked,
    response_model_exclude_unset=True,
)
async def get_user(
    user_id: int,
    optional_login: ent.User | None = Depends(m.optional_login),
    user_manager: m.UserManager = Depends(m.UserManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    user_db = await user_manager.detail_load(user_id)
    auth.authorize(optional_login, "read", user_db, oso)
    return auth.get_authorized_output_fields(optional_login, "read", user_db, oso)


@user_router.patch(
    "/user/{user_id}",
    response_model=s.UserRead,
    response_model_exclude_unset=True,
)
async def update_user(
    user_id: int,
    user: Annotated[
        s.UserUpdate, Body(example={"first_name": "Henk", "last_name": "de Vries"})
    ],
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
    required_login=Depends(m.required_login),
    user_manager: m.UserManager = Depends(m.UserManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    user_db = await user_manager.min_load(user_id)
    auth.authorize(required_login, "delete", user_db, oso)
    await user_manager.delete(user_db, request=request)
    return Response(status_code=204)


@user_router.get(
    "/users", response_model=s.UserReadList, response_model_exclude_unset=True
)
async def get_users(
    session: AsyncSession = Depends(get_async_session),
    optional_user: ent.User | None = Depends(m.optional_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
    offset: int = 0,
    limit: int = 20,
    email: str | None = None,
):
    query = get_users_q(optional_user, email, offset, limit)

    users_result = await session.execute(query)
    users_scalar = users_result.scalars().all()

    filtered_users = [
        auth.get_authorized_output_fields(optional_user, "read", i, oso)
        for i in users_scalar
    ]
    return s.UserReadList(users=filtered_users)


@user_router.post("/user/{user_id}/profile-picture")
async def upload_user_profile_picture(
    user_id: int,
    request: Request,
    file: UploadFile = File(...),
    user_manager: m.UserManager = Depends(m.UserManager),
    required_user: ent.User = Depends(m.required_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    user_db = await user_manager.detail_load(user_id)
    auth.authorize(required_user, "edit", user_db, oso)
    await user_manager.profile_picture_handler.set(file, user_db, request)


@user_router.delete("/user/{user_id}/profile-picture")
async def delete_user_profile_picture(
    user_id: int,
    request: Request,
    user_manager: m.UserManager = Depends(m.UserManager),
    required_user: ent.User = Depends(m.required_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    user_db = await user_manager.detail_load(user_id)
    auth.authorize(required_user, "edit", user_db, oso)
    await user_manager.profile_picture_handler.delete(user_db, request)
    return Response(status_code=204)


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
    user_id: int = Path(..., examples={"1": {"summary": "1", "value": 1}}),
    institution_id: str = Query(
        ...,
        examples={
            "ING": {"summary": "ING", "value": "ING_INGBNL2A"},
            "SANDBOX": {"summary": "SANDBOX", "value": "SANDBOXFINANCE_SFIN0000"},
        },
    ),
    n_days_access: int = Query(..., examples={"7": {"summary": "7", "value": 7}}),
    n_days_history: int = Query(..., examples={"7": {"summary": "7", "value": 7}}),
    session: AsyncSession = Depends(get_async_session),
    required_user=Depends(m.required_login),
    user_manager: m.UserManager = Depends(m.UserManager),
    client: NordigenClient = Depends(get_nordigen_client),
):
    await s.validate_institution_id(institution_id)
    await s.validate_n_days_access(n_days_access)
    await s.validate_n_days_history(institution_id, n_days_history)

    # TODO: Ensure only users can link for themselves.
    user = await user_manager.min_load(user_id)

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

    init = await client.initialize_session(
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
    url = os.environ["SPA_GOCARDLESS_CALLBACK_REDIRECT_URL"]

    if error is not None:
        audit_logger.error(f"Third party GoCardless callback error with {error=}")
        return RedirectResponse(url.format(message="third-party-error"))

    try:
        payload = jwt.decode(ref, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        audit_logger.error(f"JTW token expired on GoCardless callback")
        return RedirectResponse(url=url.format(message="jwt-token-expired"))
    except JWTError:
        audit_logger.error(f"JWT token could not be validated on GoCardless callback")
        return RedirectResponse(url=url.format(message="jwt-validation-error"))

    if payload["user_id"] != user_id:
        audit_logger.error(
            f"User could not be found on GoCardless callback with {user_id=}"
        )
        return RedirectResponse(url=url.format(message="user-404"))

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
        audit_logger.error(f"Requisition could not be found on Gocardless callback")
        return RedirectResponse(url=url.format(message="requisition-404"))

    requisition.callback_handled = True
    session.add(requisition)
    await session.commit()

    background_tasks.add_task(
        get_gocardless_payments,
        requisition.id,
        datetime.today() - timedelta(days=requisition.n_days_history + 1),
    )
    url = url.format(message="success")
    return RedirectResponse(url=url)


@user_router.get(
    "/user/{user_id}/bank-account/{bank_account_id}",
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
    "/user/{user_id}/bank-account/{bank_account_id}",
    response_model=s.BankAccountRead,
)
async def revoke_bank_account(
    user_id: int,
    bank_account_id: int,
    request: Request,
    required_user=Depends(m.required_login),
    bank_account_manager: m.BankAccountManager = Depends(m.BankAccountManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    bank_account_db = await bank_account_manager.detail_load(bank_account_id)
    auth.authorize(required_user, "revoke", bank_account_db, oso)
    bank_account_db = await bank_account_manager.revoke(
        bank_account_db, request=request
    )
    return auth.get_authorized_output_fields(
        required_user, "read", bank_account_db, oso
    )


@user_router.delete("/user/{user_id}/bank-account/{bank_account_id}")
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
    "/user/{user_id}/bank-account/{bank_account_id}/users",
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


@initiative_router.get(
    "/initiative/{initiative_id}/media", response_model=s.AttachmentList
)
async def get_initiative_media(
    initiative_id: int,
    session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(m.optional_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
    offset: int = 0,
    limit: int = 20,
):
    # TODO: Is initiative hidden? Also for other routes.
    query = await get_initiative_media_q(
        optional_user,
        initiative_id,
        offset,
        limit,
    )

    media_result = await session.execute(query)
    media_scalar = media_result.scalars().all()

    filtered_media = [
        auth.get_authorized_output_fields(optional_user, "read", i, oso)
        for i in media_scalar
    ]

    return s.AttachmentList(attachments=filtered_media)


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
    initiative_db = await initiative_manager.detail_load(initiative_id)
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
    initiative_db = await initiative_manager.detail_load(initiative_id)
    auth.authorize(required_user, "delete", initiative_db, oso)
    await initiative_manager.delete(initiative_db, request=request)
    return Response(status_code=204)


@initiative_router.post("/initiative/{initiative_id}/profile-picture")
async def upload_initiative_profile_picture(
    initiative_id: int,
    request: Request,
    file: UploadFile = File(...),
    initiative_manager: m.InitiativeManager = Depends(m.InitiativeManager),
    required_user: ent.User = Depends(m.required_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    initiative_db = await initiative_manager.detail_load(initiative_id)
    auth.authorize(required_user, "edit", initiative_db, oso)
    await initiative_manager.profile_picture_handler.set(
        file, initiative_db, request=request
    )


@initiative_router.delete("/initiative/{initiative_id}/profile-picture")
async def delete_initiative_profile_picture(
    initiative_id: int,
    request: Request,
    initiative_manager: m.InitiativeManager = Depends(m.InitiativeManager),
    required_user: ent.User = Depends(m.required_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    initiative_db = await initiative_manager.detail_load(initiative_id)
    auth.authorize(required_user, "edit", initiative_db, oso)
    await initiative_manager.profile_picture_handler.delete(
        initiative_db, request=request
    )
    return Response(status_code=204)


@initiative_router.get(
    "/initiatives",
    response_model=s.InitiativeReadList,
    response_model_exclude_unset=True,
)
async def get_initiatives(
    session: AsyncSession = Depends(get_async_session),
    optional_user: ent.User | None = Depends(m.optional_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
    offset: int = 0,
    limit: int = 20,
    name: str | None = None,
    only_mine: bool = False,
):
    query = get_initiatives_q(optional_user, name, only_mine, offset, limit)
    initiatives_result = await session.execute(query)
    initiatives_scalar = initiatives_result.scalars().all()

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
    initiative_db = await initiative_manager.detail_load(initiative_id)
    auth.authorize(required_user, "create_activity", initiative_db, oso)
    activity_db = await activity_manager.create(
        activity, initiative_id, request=request
    )
    activity_db = await activity_manager.detail_load(activity_db.id)
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
    activity_db = await activity_manager.detail_load(activity_id)
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
    activity_db = await activity_manager.detail_load(activity_id)
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
    activity_db = await activity_manager.detail_load(activity_id)
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
    activity_db = await activity_manager.detail_load(activity_id)
    auth.authorize(required_user, "delete", activity_db, oso)
    await activity_manager.delete(activity_db, request=request)
    return Response(status_code=204)


@initiative_router.post(
    "/initiative/{initiative_id}/activity/{activity_id}/profile-picture"
)
async def upload_activity_profile_picture(
    initiative_id: int,
    activity_id: int,
    request: Request,
    file: UploadFile = File(...),
    activity_manager: m.ActivityManager = Depends(m.ActivityManager),
    required_user: ent.User = Depends(m.required_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    activity_db = await activity_manager.detail_load(activity_id)
    auth.authorize(required_user, "edit", activity_db, oso)
    await activity_manager.profile_picture_handler.set(
        file, activity_db, request=request
    )


@initiative_router.delete(
    "/initiative/{initiative_id}/activity/{activity_id}/profile-picture"
)
async def delete_activity_profile_picture(
    initiative_id: int,
    activity_id: int,
    request: Request,
    activity_manager: m.ActivityManager = Depends(m.ActivityManager),
    required_user: ent.User = Depends(m.required_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    activity_db = await activity_manager.detail_load(activity_id)
    auth.authorize(required_user, "edit", activity_db, oso)
    await activity_manager.profile_picture_handler.delete(activity_db, request=request)
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
    funder: Annotated[
        s.FunderCreate,
        Body(example={"name": "Gemeente Amsterdam", "url": "https://amsterdam.nl"}),
    ],
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
    session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(m.optional_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
    offset: int = 0,
    limit: int = 20,
    name: str | None = None,
):
    query = get_funders_q(name, offset, limit)

    funders_result = await session.execute(query)
    funders_scalar = funders_result.scalars().all()

    filtered_funders = [
        auth.get_authorized_output_fields(optional_user, "read", i, oso)
        for i in funders_scalar
    ]

    return s.FunderReadList(funders=filtered_funders)


@funder_router.post("/funder/{funder_id}/regulation", response_model=s.RegulationRead)
async def create_regulation(
    funder_id: int,
    regulation: Annotated[
        s.RegulationCreate,
        Body(
            example={
                "name": "Buurtprojecten",
                "description": "Buurtprojecten in Amsterdam Oost.",
            }
        ),
    ],
    request: Request,
    required_user=Depends(m.required_login),
    funder_manager: m.FunderManager = Depends(m.FunderManager),
    regulation_manager: m.RegulationManager = Depends(m.RegulationManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    funder_db = await funder_manager.min_load(funder_id)
    auth.authorize(required_user, "create_regulation", funder_db, oso)
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
    session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(m.optional_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
    offset: int = 0,
    limit: int = 20,
    name: str | None = None,
):
    query = get_regulations_q(funder_id, name, offset, limit)

    regulations_result = await session.execute(query)
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
    grant: Annotated[
        s.GrantCreate,
        Body(
            example={
                "name": "Boerenmarkt op Westerplein",
                "reference": "AO-1991",
                "budget": 1000.00,
            }
        ),
    ],
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
    "/funder/{funder_id}/regulation/{regulation_id}/grant/{grant_id}/overseers",
    response_model=s.UserReadList,
    responses={204: {"description": "Grant overseer is removed"}},
)
async def link_overseers(
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
    offset: int = 0,
    limit: int = 20,
    name: str | None = None,
):
    query = get_grants_q(regulation_id, name, offset, limit)

    grants_result = await async_session.execute(query)
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
    grant_db = await grant_manager.detail_load(grant_id)
    auth.authorize(required_user, "create_initiative", grant_db, oso)
    # TODO: Validate funder_id, regulation_id and grant_id.
    initiative_db = await initiative_manager.create(
        initiative, grant_id, request=request
    )
    # TODO: If we don't do this, profile_picture will have a Greenlet exception for retrieving data
    # outside of asynchronous context.
    await initiative_manager.session.refresh(initiative_db)
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
    # TODO: Make sure initiative_id in the schema is congruent with activity_id.
    if payment.activity_id is not None:
        activity_db = await activity_manager.detail_load(payment.activity_id)
        if activity_db.initiative_id != payment.initiative_id:
            raise EntityNotFound("There exists no activity with this initiative id")
        auth.authorize(required_user, "create_payment", activity_db, oso)
    else:
        initiative_db = await initiative_manager.detail_load(payment.initiative_id)
        auth.authorize(required_user, "create_payment", initiative_db, oso)

    payment_db = await payment_manager.create(
        payment, payment.initiative_id, payment.activity_id, request=request
    )
    # TODO: Also see user. How to deal with this?
    await payment_db.awaitable_attrs.attachments
    return auth.get_authorized_output_fields(required_user, "read", payment_db, oso)


@payment_router.get("/payment/{payment_id}", response_model=s.PaymentReadLinked)
async def get_payment(
    payment_id: int,
    optional_login: ent.User | None = Depends(m.optional_login),
    payment_manager: m.PaymentManager = Depends(m.PaymentManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    payment_db = await payment_manager.detail_load(payment_id)
    auth.authorize(optional_login, "read", payment_db, oso)
    return auth.get_authorized_output_fields(optional_login, "read", payment_db, oso)


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
    payment_db = await payment_manager.detail_load(payment_id)
    auth.authorize(required_user, "edit", payment_db, oso)
    auth.authorize_input_fields(required_user, "edit", payment_db, payment)
    edited_payment = await payment_manager.update(payment, payment_db, request=request)
    return auth.get_authorized_output_fields(required_user, "read", edited_payment, oso)


@payment_router.patch(
    "/payment/{payment_id}/initiative",
    response_model=Union[s.InitiativeRead, s.PaymentUncoupled],
    response_model_exclude_unset=True,
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
    auth.authorize(required_user, "link_initiative", payment_db, oso)

    if payment.initiative_id is not None:
        initiative_db = await initiative_manager.detail_load(payment.initiative_id)
        auth.authorize(required_user, "link_payment", initiative_db, oso)

    payment_db = await payment_manager.assign_payment_to_initiative(
        payment_db,
        payment.initiative_id,
        request=request,
    )

    if payment.initiative_id is not None:
        return auth.get_authorized_output_fields(
            required_user, "read", initiative_db, oso
        )
    else:
        return s.PaymentUncoupled(
            message="Payment was successfully uncoupled from the initiative."
        )


@payment_router.patch(
    "/payment/{payment_id}/activity",
    response_model=Union[s.ActivityRead, s.PaymentUncoupled],
    response_model_exclude_unset=True,
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
    auth.authorize(required_user, "link_activity", payment_db, oso)

    if payment.activity_id is not None:
        activity_db = await activity_manager.detail_load(payment.activity_id)
        if activity_db.initiative_id != payment.initiative_id:
            raise EntityNotFound("There exists no activity with this initiative id")
        auth.authorize(required_user, "link_payment", activity_db, oso)

    payment_db = await payment_manager.assign_payment_to_activity(
        payment_db, payment.activity_id, request=request
    )

    if payment.activity_id is not None:
        return auth.get_authorized_output_fields(
            required_user, "read", activity_db, oso
        )
    else:
        return s.PaymentUncoupled(
            message="Payment was successfully uncoupled from the activity."
        )


@payment_router.delete("/payment/{payment_id}")
async def delete_payment(
    payment_id: int,
    request: Request,
    required_user=Depends(m.required_login),
    payment_manager: m.PaymentManager = Depends(m.PaymentManager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    payment_db = await payment_manager.detail_load(payment_id)
    auth.authorize(required_user, "delete", payment_db, oso)
    await payment_manager.delete(payment_db, request=request)
    return Response(status_code=204)


@payment_router.post("/payment/{payment_id}/attachments")
async def upload_payment_attachments(
    payment_id: int,
    request: Request,
    files: list[UploadFile] = File(...),
    payment_manager: m.PaymentManager = Depends(m.PaymentManager),
    required_user: ent.User = Depends(m.required_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    payment_db = await payment_manager.detail_load(payment_id)
    auth.authorize(required_user, "edit", payment_db, oso)
    await payment_manager.attachment_handler.set(files, payment_db, request)


@payment_router.delete("/payment/{payment_id}/attachment/{attachment_id}")
async def delete_payment_attachment(
    payment_id: int,
    attachment_id: int,
    request: Request,
    payment_manager: m.PaymentManager = Depends(m.PaymentManager),
    required_user: ent.User = Depends(m.required_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    payment_db = await payment_manager.detail_load(payment_id)
    auth.authorize(required_user, "edit", payment_db, oso)
    await payment_manager.attachment_handler.delete(payment_db, attachment_id, request)


@payment_router.get(
    "/payments/bng",
    response_model=s.PaymentReadUserList,
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
    response_model=s.PaymentReadUserList,
    response_model_exclude_unset=True,
)
async def get_user_payments(
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    required_user=Depends(m.required_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
    offset: int = 0,
    limit: int = 20,
    initiative_name: str | None = None,
    activity_name: str | None = None,
    iban: str | None = None,
):
    if required_user.id != user_id:
        raise NotAuthorized("Not authorized")

    query = get_user_payments_q(
        user_id, initiative_name, activity_name, iban, offset, limit
    )

    payments_result = await session.execute(query)
    payments_scalar = payments_result.all()

    # For every payment, determine if it's linkable to/from initiatives/activities.
    payments_with_linkability = []
    for row in payments_scalar:
        payments_with_linkability.append(
            {
                **row._mapping,
                "linkable_initiative": auth.is_allowed(
                    required_user, "link_initiative", row.t[0]
                ),
                "linkable_activity": auth.is_allowed(
                    required_user, "link_activity", row.t[0]
                ),
            }
        )

    payments = [s.PaymentReadUser(**i) for i in payments_with_linkability]

    return s.PaymentReadUserList(payments=payments)


@payment_router.get(
    "/payments/initiative/{initiative_id}",
    response_model=s.PaymentReadInitiativeList,
    response_model_exclude_unset=True,
)
async def get_initiative_payments(
    initiative_id: int,
    session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(m.optional_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
    offset: int = 0,
    limit: int = 20,
    start_date: date | None = None,
    end_date: date | None = None,
    min_amount: s.TransactionAmount | None = None,
    max_amount: s.TransactionAmount | None = None,
    route: ent.Route | None = None,
):
    # TODO: What is initiatie is hidden?
    query = get_initiative_payments_q(
        optional_user,
        initiative_id,
        offset,
        limit,
        start_date,
        end_date,
        min_amount,
        max_amount,
        route,
    )

    payments_result = await session.execute(query)
    payments_scalar = payments_result.all()

    payments = [s.PaymentReadInitiative(**i._mapping) for i in payments_scalar]

    return s.PaymentReadInitiativeList(payments=payments)


@payment_router.get(
    "/payments/initiative/{initiative_id}/activity/{activity_id}",
    response_model=s.PaymentReadActivityList,
    response_model_exclude_unset=True,
)
async def get_activity_payments(
    initiative_id: int,
    activity_id: int,
    session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(m.optional_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
    offset: int = 0,
    limit: int = 20,
    start_date: date | None = None,
    end_date: date | None = None,
    min_amount: s.TransactionAmount | None = None,
    max_amount: s.TransactionAmount | None = None,
    route: ent.Route | None = None,
):
    # What if activity is hidden?
    query = get_activity_payments_q(
        optional_user,
        activity_id,
        offset,
        limit,
        start_date,
        end_date,
        min_amount,
        max_amount,
        route,
    )

    payments_result = await session.execute(query)
    payments_scalar = payments_result.all()

    payments = [s.PaymentReadActivity(**i._mapping) for i in payments_scalar]

    return s.PaymentReadActivityList(payments=payments)


@permission_router.get("/actions", response_model=s.AuthActionsRead)
async def get_authorized_actions(
    entity_class: s.AuthEntityClass,
    entity_id: int | None = None,
    optional_user: ent.User | None = Depends(m.optional_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
    user_manager: m.UserManager = Depends(m.UserManager),
    funder_manager: m.FunderManager = Depends(m.FunderManager),
    regulation_manager: m.RegulationManager = Depends(m.RegulationManager),
    grant_manager: m.GrantManager = Depends(m.GrantManager),
    bank_account_manager: m.BankAccountManager = Depends(m.BankAccountManager),
    initiative_manager: m.InitiativeManager = Depends(m.InitiativeManager),
    activity_manager: m.ActivityManager = Depends(m.ActivityManager),
    payment_manager: m.PaymentManager = Depends(m.PaymentManager),
):
    class_map: dict[s.AuthEntityClass, m.BaseManager] = {
        s.AuthEntityClass.USER: user_manager,
        s.AuthEntityClass.FUNDER: funder_manager,
        s.AuthEntityClass.REGULATION: regulation_manager,
        s.AuthEntityClass.GRANT: grant_manager,
        s.AuthEntityClass.BANK_ACCOUNT: bank_account_manager,
        s.AuthEntityClass.INITIATIVE: initiative_manager,
        s.AuthEntityClass.ACTIVITY: activity_manager,
        s.AuthEntityClass.PAYMENT: payment_manager,
    }

    resource: ent.Base | s.AuthEntityClass
    if entity_id is not None:
        resource = await class_map[entity_class].detail_load(entity_id)
    else:
        resource = entity_class

    return s.AuthActionsRead(
        actions=auth.get_authorized_actions(optional_user, resource, oso)
    )


@permission_router.get("/edit-fields", response_model=s.AuthFieldsRead)
async def get_authorized_fields(
    entity_class: s.AuthEntityClass,
    entity_id: int,
    async_session: AsyncSession = Depends(get_async_session),
    optional_user: ent.User | None = Depends(m.optional_login),
    oso=Depends(auth.set_sqlalchemy_adapter),
    user_manager: m.UserManager = Depends(m.UserManager),
    funder_manager: m.FunderManager = Depends(
        m.FunderManager,
    ),
    regulation_manager: m.RegulationManager = Depends(m.RegulationManager),
    grant_manager: m.GrantManager = Depends(m.GrantManager),
    bank_account_manager: m.BankAccountManager = Depends(m.BankAccountManager),
    initiative_manager: m.InitiativeManager = Depends(m.InitiativeManager),
    activity_manager: m.ActivityManager = Depends(m.ActivityManager),
    payment_manager: m.PaymentManager = Depends(m.PaymentManager),
):
    class_map: dict[s.AuthEntityClass, m.BaseManager] = {
        s.AuthEntityClass.USER: user_manager,
        s.AuthEntityClass.FUNDER: funder_manager,
        s.AuthEntityClass.REGULATION: regulation_manager,
        s.AuthEntityClass.GRANT: grant_manager,
        s.AuthEntityClass.BANK_ACCOUNT: bank_account_manager,
        s.AuthEntityClass.INITIATIVE: initiative_manager,
        s.AuthEntityClass.ACTIVITY: activity_manager,
        s.AuthEntityClass.PAYMENT: payment_manager,
    }

    resource = await class_map[entity_class].detail_load(entity_id)

    return s.AuthFieldsRead(
        fields=auth.get_authorized_fields(optional_user, "edit", resource)
    )


@permission_router.get("/linkable-initiatives", response_model=s.LinkableInitiatives)
async def get_linkable_initiatives(
    session: AsyncSession = Depends(get_async_session),
    required_user: ent.User = Depends(m.required_login),
):
    query = get_linkable_initiatives_q(required_user)

    initiatives_result = await session.execute(query)
    initiatives_scalar = initiatives_result.all()

    # For every initiative, determine if it's possible to link a payment to it.
    linkable_initiatives = []
    for row in initiatives_scalar:
        if auth.is_allowed(required_user, "link_payment", row.t[0]):
            linkable_initiatives.append(row._mapping)

    initiatives = [s.LinkableInitiative(**i) for i in linkable_initiatives]

    return s.LinkableInitiatives(initiatives=initiatives)


@permission_router.get(
    "/initiative/{initiative_id}/linkable-activities",
    response_model=s.LinkableActivities,
)
async def get_linkable_activities(
    initiative_id: int,
    session: AsyncSession = Depends(get_async_session),
    required_user: ent.User = Depends(m.required_login),
):
    query = get_linkable_activities_q(required_user, initiative_id)

    activities_result = await session.execute(query)
    activities_scalar = activities_result.all()

    # For every activity, determine if it's possible to link a payment to it.
    linkable_activities = []
    for row in activities_scalar:
        if auth.is_allowed(required_user, "link_payment", row.t[0]):
            linkable_activities.append(row._mapping)

    activities = [s.LinkableActivity(**i) for i in linkable_activities]

    return s.LinkableActivities(activities=activities)


@utils_router.get(
    "/utils/gocardless/institutions", response_model=GoCardlessInstitutionList
)
async def get_institutions(
    request: Request,
    institutions: GoCardlessInstitutionList = Depends(get_institutions_from_gocardless),
):
    return institutions
