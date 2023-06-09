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
from ..database import get_async_session
from .. import schemas_and_models as s
from ..schemas_and_models.models import entities as ent
from .. import authorization as auth
from ..utils.utils import temp_password_generator, get_requester_ip
import os
from ..bng.api import create_consent
from ..bng import get_bng_payments, retrieve_access_token, create_consent
from jose import jwt, JWTError, ExpiredSignatureError

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from requests import RequestException
from datetime import datetime, timedelta, date
from time import time
import pytz


DOMAIN_NAME = os.environ.get("DOMAIN_NAME")
SPA_BNG_CALLBACK_REDIRECT_URL = os.environ.get("SPA_BNG_CALLBACK_REDIRECT_URL")


user_router = APIRouter()

# We define dependencies this way because we can otherwise not override them
# easily during testing.
superuser_dep = auth.fastapi_users.current_user(superuser=True)


@user_router.post("/user", response_model=s.UserRead)
async def create_user(
    user: s.UserCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    superuser=Depends(superuser_dep),
    user_manager: auth.UserManager = Depends(auth.get_user_manager),
):
    user_with_password = s.UserCreateWithPassword(
        **user.dict(), password=temp_password_generator(16)
    )
    try:
        new_user = await user_manager.create(user_with_password, request=request)
    except UserAlreadyExists:
        raise HTTPException(status_code=400, detail="Email address already registered")
    await session.refresh(new_user)
    return s.UserRead.from_orm(new_user)


@user_router.patch(
    "/user/{user_id}",
    response_model=s.UserRead,
    response_model_exclude_unset=True,
)
@user_router.patch("/user/{user_id}")
async def update_user(
    user_id: int,
    user: s.UserUpdate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user=Depends(auth.fastapi_users.current_user(optional=True)),
    user_manager: auth.UserManager = Depends(auth.get_user_manager),
):
    user_db = await session.get(ent.User, user_id)
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        edited_user = await user_manager.update(user, user_db, request=request)
    except UserAlreadyExists:
        raise HTTPException(status_code=400, detail="Email address already registered")
    return s.UserRead.from_orm(edited_user)


@user_router.delete("/user/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    superuser=Depends(superuser_dep),
    user_manager: auth.UserManager = Depends(auth.get_user_manager),
):
    user = await session.get(ent.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await user_manager.delete(user, request=request)
    return Response(status_code=204)


@user_router.get(
    "/users", response_model=s.UserReadList, response_model_exclude_unset=True
)
async def get_users(
    session: AsyncSession = Depends(get_async_session),
    current_user=Depends(auth.fastapi_users.current_user(optional=True)),
):
    # TODO: Enable searching by email.
    # TODO: pagination.
    users = await session.execute(select(ent.User))
    return s.UserReadList(users=users.scalars().all())


import re


def validate_iban(iban: str = Query(...)):
    # Roughly validate an IBAN: begins with two uppercase letters followed by 2 digits and up to 30 alphanumeric characters
    if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]{1,30}$", iban):
        raise HTTPException(status_code=400, detail="Invalid IBAN format")
    return iban


def validate_expires_on(expires_on: date = Query(...)):
    amsterdam_tz = pytz.timezone("Europe/Amsterdam")
    today = datetime.now(amsterdam_tz).date()
    if expires_on < today:
        raise HTTPException(
            status_code=400, detail="expires_on should not be before today"
        )
    elif expires_on > (today + timedelta(days=90)):
        raise HTTPException(
            status_code=400,
            detail="expires_on should not be later than 90 days from now",
        )
    return expires_on


# BNG
@user_router.get(
    "/users/{user_id}/bng-initiate",
    response_model=s.BNGInitiate,
)
async def bng_initiate(
    user_id: int,
    iban: str = Depends(validate_iban),
    expires_on: date = Depends(validate_expires_on),
    session: AsyncSession = Depends(get_async_session),
    current_user=Depends(auth.fastapi_users.current_user(optional=True)),
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
            "iban": iban,
            "bank_name": "BNG",
            "exp": time() + 1800,
            "consent_id": consent_id,
        },
        auth.SECRET_KEY,
        auth.ALGORITHM,
    )
    url_to_return = oauth_url.format(token)
    return s.BNGInitiate(url=url_to_return)


@user_router.post("/users/{user_id}/bng-callback")
async def bng_callback(
    user_id: int,
    background_tasks: BackgroundTasks,
    code: str = Query(),
    state: str = Query(),
    session: AsyncSession = Depends(get_async_session),
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
    return RedirectResponse(url=SPA_BNG_CALLBACK_REDIRECT_URL)


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
