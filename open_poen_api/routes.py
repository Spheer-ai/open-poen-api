from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    BackgroundTasks,
    Query,
)
from fastapi.responses import RedirectResponse
from fastapi_users.exceptions import UserAlreadyExists
from .database import get_async_session
from . import schemas_and_models as s
from .schemas_and_models.models import entities as ent
from . import user_manager as um
from . import initiative_manager as im
from .utils.utils import temp_password_generator, get_requester_ip
import os
from .bng.api import create_consent
from .bng import get_bng_payments, retrieve_access_token, create_consent
from jose import jwt, JWTError, ExpiredSignatureError

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import noload
from requests import RequestException
from datetime import datetime, timedelta, date
from time import time
import pytz
from typing import Set, Any
from oso import exceptions
from .authorization.authorization import SECRET_KEY, ALGORITHM
from .authorization import authorization as auth


router = APIRouter()

# We define dependencies this way because we can otherwise not override them
# easily during testing.
superuser_dep = um.fastapi_users.current_user(superuser=True)
required_login_dep = um.fastapi_users.current_user(optional=False)
optional_login_dep = um.fastapi_users.current_user(optional=True)


@router.post("/user", response_model=s.UserRead)
async def create_user(
    user: s.UserCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    superuser=Depends(superuser_dep),
    user_manager: um.UserManager = Depends(um.get_user_manager),
):
    auth.authorize(superuser, "create", ent.User)
    user_with_password = s.UserCreateWithPassword(
        **user.dict(), password=temp_password_generator(16)
    )
    try:
        user_db = await user_manager.create(user_with_password, request=request)
    except UserAlreadyExists:
        raise HTTPException(status_code=400, detail="Email address already registered")
    await session.refresh(user_db)
    return auth.get_authorized_output_fields(superuser, "read", user_db)


@router.get(
    "/user/{user_id}",
    response_model=s.UserReadLinked,
    response_model_exclude_unset=True,
)
async def get_initiative(
    user_id: int,
    session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(optional_login_dep),
    user_manager: um.UserManager = Depends(im.get_initiative_manager),
):
    user_db = await session.get(ent.User, user_id)
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")
    auth.authorize(optional_user, "read", user_db)
    return auth.get_authorized_output_fields(optional_user, "read", user_db)


@router.patch(
    "/user/{user_id}",
    response_model=s.UserRead,
    response_model_exclude_unset=True,
)
async def update_user(
    user_id: int,
    user: s.UserUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    required_user=Depends(required_login_dep),
    user_manager: um.UserManager = Depends(um.get_user_manager),
):
    user_db = await session.get(ent.User, user_id)
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")
    auth.authorize(required_user, "edit", user_db)
    auth.authorize_input_fields(required_user, "edit", user_db, user)
    try:
        edited_user = await user_manager.update(user, user_db, request=request)
    except UserAlreadyExists:
        raise HTTPException(status_code=400, detail="Email address already registered")
    await session.refresh(edited_user)
    return auth.get_authorized_output_fields(required_user, "read", edited_user)


@router.delete("/user/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    superuser=Depends(superuser_dep),
    user_manager: um.UserManager = Depends(um.get_user_manager),
):
    user_db = await session.get(ent.User, user_id)
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")
    auth.authorize(superuser, "delete", user_db)
    await user_manager.delete(user_db, request=request)
    return Response(status_code=204)


@router.get("/users", response_model=s.UserReadList, response_model_exclude_unset=True)
async def get_users(
    session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(optional_login_dep),
):
    # TODO: Enable searching by email.
    # TODO: pagination.
    q = auth.get_authorized_query(optional_user, "read", ent.User)

    users_result = await session.execute(
        q.options(noload(ent.User.initiatives), noload(ent.User.bng))
    )
    filtered_users = [
        auth.get_authorized_output_fields(optional_user, "read", i)
        for i in users_result.scalars().all()
    ]
    return s.UserReadList(users=filtered_users)


# BNG
@router.get(
    "/users/{user_id}/bng-initiate",
    response_model=s.BNGInitiate,
)
async def bng_initiate(
    user_id: int,
    iban: str = Depends(s.validate_iban),
    expires_on: date = Depends(s.validate_expires_on),
    session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(optional_login_dep),  # TODO
    requester_ip: str = Depends(get_requester_ip),
):
    user = await session.get(ent.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_bng = await session.execute(select(ent.BNG))
    if existing_bng.first():
        raise HTTPException(
            status_code=400,
            detail=f"A BNG Account with IBAN {existing_bng.iban} is already linked.",
        )
    try:
        consent_id, oauth_url = create_consent(
            iban=iban,
            valid_until=expires_on,
            redirect_url=f"https://{os.environ.get('DOMAIN_NAME')}/users/{user_id}/bng-callback",
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


@router.get("/users/{user_id}/bng-callback")
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
    await session.refresh(new_bng_account)
    # background_tasks.add_task(get_bng_payments, session)  # TODO
    return RedirectResponse(url=os.environ.get("SPA_BNG_CALLBACK_REDIRECT_URL"))


# @router.delete("/users/{user_id}/bng-connection")
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


# # GOCARDLESS
# @router.get("/users/{user_id}/gocardless-initiate", response_class=RedirectResponse)
# async def gocardless_initiatite(
#     user_id: int,
#     # gocardless: s.GoCardlessCreateActivityOwnerCreate,
#     logged_in_user=Depends(auth.get_logged_in_user),
#     requires_user_owner=Depends(auth.requires_user_owner),
#     session: AsyncSession = Depends(get_async_session),
# ):
#     user = session.get(ent.User, user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")

#     # A user can only have one requisition per bank (institution_id).
#     # TODO

#     await refresh_tokens()

#     init = client.initialize_session(
#         # TODO: This has to redirect to the SPA.
#         redirect_uri=f"https://{DOMAIN_NAME}/users/{user_id}/gocardless-callback",
#         # TODO: Parse dynamically
#         institution_id="ING_INGBNL2A",
#         reference_id=format_user_timestamp(user.id),
#         max_historical_days=720,
#     )

#     new_requisition = ent.Requisition(
#         user_id=user_id,
#         api_institution_id="ING_INGBNL2A",
#         api_requisition_id=init.requisition_id,
#     )
#     session.add(new_requisition)
#     session.commit()
#     # TODO: Don´t return a redirect, but some json with the link.
#     return RedirectResponse(url=init.link)


@router.post("/initiative", response_model=s.InitiativeRead)
async def create_initiative(
    initiative: s.InitiativeCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    required_user=Depends(required_login_dep),
    initiative_manager: im.InitiativeManager = Depends(im.get_initiative_manager),
):
    auth.authorize(required_user, "create", ent.Initiative)
    try:
        initiative_db = await initiative_manager.create(initiative, request=request)
    except im.InitiativeAlreadyExists:
        raise HTTPException(status_code=400, detail="Name already registered")
    await session.refresh(initiative_db)
    return auth.get_authorized_output_fields(required_user, "read", initiative_db)


@router.get(
    "/initiative/{initiative_id}",
    response_model=s.InitiativeReadLinked,
    response_model_exclude_unset=True,
)
async def get_initiative(
    initiative_id: int,
    session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(optional_login_dep),
    initiative_manager: im.InitiativeManager = Depends(im.get_initiative_manager),
):
    initiative_db = await initiative_manager.fetch_and_verify(initiative_id)
    auth.authorize(optional_user, "read", initiative_db)
    return auth.get_authorized_output_fields(optional_user, "read", initiative_db)


@router.patch(
    "/initiative/{initiative_id}",
    response_model=s.InitiativeRead,
    response_model_exclude_unset=True,
)
async def update_initiative(
    initiative_id: int,
    initiative: s.InitiativeUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    required_user=Depends(required_login_dep),
    initiative_manager: im.InitiativeManager = Depends(im.get_initiative_manager),
):
    initiative_db = await initiative_manager.fetch_and_verify(initiative_id)
    auth.authorize(required_user, "edit", initiative_db)
    auth.authorize_input_fields(required_user, "edit", initiative_db, initiative)
    try:
        edited_initiative = await initiative_manager.update(
            initiative, initiative_db, request=request
        )
    except im.InitiativeAlreadyExists:
        raise HTTPException(status_code=400, detail="Name already registered")
    await session.refresh(edited_initiative)
    return auth.get_authorized_output_fields(required_user, "read", edited_initiative)


@router.patch(
    "/initiative/{initiative_id}/owners",
    response_model=s.UserReadList,
)
async def link_initiative_owners(
    initiative_id: int,
    initiative: s.InitiativeOwnersUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    required_user=Depends(required_login_dep),
    initiative_manager: im.InitiativeManager = Depends(im.get_initiative_manager),
):
    initiative_db = await initiative_manager.fetch_and_verify(initiative_id)
    auth.authorize(required_user, "edit", initiative_db)
    initiative_db = await initiative_manager.make_users_owner(
        initiative_db, initiative.user_ids, request=request
    )
    await session.refresh(initiative_db)
    return s.UserReadList(
        users=initiative_db.initiative_owners
    )  # TODO: How to filter these fields?


@router.delete("/initiative/{initiative_id}")
async def delete_initiative(
    initiative_id: int,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    required_user=Depends(required_login_dep),
    initiative_manager: im.InitiativeManager = Depends(im.get_initiative_manager),
):
    initiative_db = await initiative_manager.fetch_and_verify(initiative_id)
    auth.authorize(required_user, "delete", initiative_db)
    await initiative_manager.delete(initiative_db, request=request)
    return Response(status_code=204)


@router.get(
    "/initiatives",
    response_model=s.InitiativeReadList,
    response_model_exclude_unset=True,
)
async def get_initiatives(
    session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(optional_login_dep),
):
    # TODO: How to authorize this?
    initiatives = await session.execute(select(ent.Initiative))
    return s.InitiativeReadList(
        initiatives=initiatives.scalars().all()
    )  # TODO: How to filter these fields?


# ROUTES
# POST "/initiative/{initiative_id}/activity",
# PATCH "/initiative/{initiative_id}/activity/{activity_id}",
# DELETE "/initiative/{initiative_id}/activity/{activity_id}"
# GET "/initiative/{initiative_id}/activities",
# POST "/initiative/{initiative_id}/activity/{activity_id}/payment",
# PATCH "/initiative/{initiative_id}/activity/{activity_id}/payment/{payment_id}",
# DELETE "/initiative/{initiative_id}/activity/{activity_id}/payment/{payment_id}",
# GET "/initiative/{initiative_id}/activity/{activity_id}/payments"
# POST "/initiative"
# PATCH "/initiative/{initiative_id}"
# DELETE "/initiative/{initiative_id}"
# GET "/initiatives"
# GET "/initiatives/aggregate-numbers"
# POST "/initiative/{initiative_id}/payment",
# PATCH "/initiative/{initiative_id}/payment/{payment_id}",
# DELETE "/initiative/{initiative_id}/payment/{payment_id}"
# GET "/initiative/{initiative_id}/payments"
# POST /debit-card,
# PATCH "/debit-card/{debit_card_id}",
# GET "/initiative/{initiative_id}/debit-cards"
# GET "/initiative/{initiative_id}/debit-cards/aggregate-numbers"
