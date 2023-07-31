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
from .database import get_async_session
from . import schemas_and_models as s
from .schemas_and_models.models import entities as ent
from .managers import user_manager as um
from .managers import initiative_manager as im
from .managers import activity_manager as am
from .utils.utils import (
    temp_password_generator,
    get_requester_ip,
    format_user_timestamp,
)
import os
from .bng.api import create_consent
from .bng import get_bng_payments, retrieve_access_token, create_consent
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
    refresh_tokens,
    client,
    INSTITUTION_ID_TO_TRANSACTION_TOTAL_DAYS,
    get_gocardless_payments,
)
import uuid


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
    superuser=Depends(superuser_dep),
    user_manager: um.UserManager = Depends(um.get_user_manager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    auth.authorize(superuser, "create", ent.User, oso)
    user_with_password = s.UserCreateWithPassword(
        **user.dict(), password=temp_password_generator(size=16)
    )
    user_db = await user_manager.create(user_with_password, request=request)
    return auth.get_authorized_output_fields(superuser, "read", user_db, oso)


@router.get(
    "/user/{user_id}",
    response_model=s.UserReadLinked,
    response_model_exclude_unset=True,
)
async def get_user(
    user_id: int,
    optional_user=Depends(optional_login_dep),
    user_manager: um.UserManager = Depends(um.get_user_manager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    user_db = await user_manager.detail_load(user_id)
    auth.authorize(optional_user, "read", user_db, oso)
    return auth.get_authorized_output_fields(optional_user, "read", user_db, oso)


@router.patch(
    "/user/{user_id}",
    response_model=s.UserRead,
    response_model_exclude_unset=True,
)
async def update_user(
    user_id: int,
    user: s.UserUpdate,
    request: Request,
    required_user=Depends(required_login_dep),
    user_manager: um.UserManager = Depends(um.get_user_manager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    user_db = await user_manager.min_load(user_id)
    auth.authorize(required_user, "edit", user_db, oso)
    auth.authorize_input_fields(required_user, "edit", user_db, user)
    edited_user = await user_manager.update(user, user_db, request=request)
    return auth.get_authorized_output_fields(required_user, "read", edited_user, oso)


@router.delete("/user/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    superuser=Depends(superuser_dep),
    user_manager: um.UserManager = Depends(um.get_user_manager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    user_db = await user_manager.min_load(user_id)
    auth.authorize(superuser, "delete", user_db, oso)
    await user_manager.delete(user_db, request=request)
    return Response(status_code=204)


@router.get("/users", response_model=s.UserReadList, response_model_exclude_unset=True)
async def get_users(
    session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(optional_login_dep),
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


# GOCARDLESS
@router.get("/users/{user_id}/gocardless-initiate", response_model=s.GocardlessInitiate)
async def gocardless_initiatite(
    user_id: int,
    institution_id: str = Depends(s.validate_institution_id),
    session: AsyncSession = Depends(get_async_session),
    required_user=Depends(required_login_dep),
    user_manager: um.UserManager = Depends(um.get_user_manager),
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
        max_historical_days=INSTITUTION_ID_TO_TRANSACTION_TOTAL_DAYS[institution_id],
    )

    requisition_db = ent.Requisition(
        user_id=user_id,
        institution_id=institution_id,
        api_requisition_id=init.requisition_id,
        reference_id=reference_id,
        status=ent.ReqStatus.CREATED,
    )
    session.add(requisition_db)
    await session.commit()

    return s.GocardlessInitiate(url=init.link)


@router.get("/users/{user_id}/gocardless-callback")
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

    await get_gocardless_payments(session, requisition.id)
    # background_tasks.add_task(get_gocardless_payments, session, requisition.id)  # TODO
    return RedirectResponse(url=os.environ.get("SPA_GOCARDLESS_CALLBACK_REDIRECT_URL"))


@router.post("/initiative", response_model=s.InitiativeRead)
async def create_initiative(
    initiative: s.InitiativeCreate,
    request: Request,
    required_user=Depends(required_login_dep),
    initiative_manager: im.InitiativeManager = Depends(im.get_initiative_manager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    auth.authorize(required_user, "create", ent.Initiative, oso)
    initiative_db = await initiative_manager.create(initiative, request=request)
    return auth.get_authorized_output_fields(required_user, "read", initiative_db, oso)


@router.get(
    "/initiative/{initiative_id}",
    response_model=s.InitiativeReadLinked,
    response_model_exclude_unset=True,
)
async def get_initiative(
    initiative_id: int,
    optional_user=Depends(optional_login_dep),
    initiative_manager: im.InitiativeManager = Depends(im.get_initiative_manager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    initiative_db = await initiative_manager.detail_load(initiative_id)
    auth.authorize(optional_user, "read", initiative_db, oso)
    return auth.get_authorized_output_fields(optional_user, "read", initiative_db, oso)


@router.patch(
    "/initiative/{initiative_id}",
    response_model=s.InitiativeRead,
    response_model_exclude_unset=True,
)
async def update_initiative(
    initiative_id: int,
    initiative: s.InitiativeUpdate,
    request: Request,
    required_user=Depends(required_login_dep),
    initiative_manager: im.InitiativeManager = Depends(im.get_initiative_manager),
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


@router.patch(
    "/initiative/{initiative_id}/owners",
    response_model=s.UserReadList,
)
async def link_initiative_owners(
    initiative_id: int,
    initiative: s.InitiativeOwnersUpdate,
    request: Request,
    required_user=Depends(required_login_dep),
    initiative_manager: im.InitiativeManager = Depends(im.get_initiative_manager),
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


@router.delete("/initiative/{initiative_id}")
async def delete_initiative(
    initiative_id: int,
    request: Request,
    required_user=Depends(required_login_dep),
    initiative_manager: im.InitiativeManager = Depends(im.get_initiative_manager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    initiative_db = await initiative_manager.min_load(initiative_id)
    auth.authorize(required_user, "delete", initiative_db, oso)
    await initiative_manager.delete(initiative_db, request=request)
    return Response(status_code=204)


@router.get(
    "/initiatives",
    response_model=s.InitiativeReadList,
    response_model_exclude_unset=True,
)
async def get_initiatives(
    async_session: AsyncSession = Depends(get_async_session),
    optional_user=Depends(optional_login_dep),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    # TODO: pagination.
    q = auth.get_authorized_query(optional_user, "read", ent.Initiative, oso)
    initiatives_result = await async_session.execute(q)
    initiatives_scalar = initiatives_result.scalars().all()
    filtered_initiatives = [
        auth.get_authorized_output_fields(optional_user, "read", i, oso)
        for i in initiatives_scalar
    ]
    return s.InitiativeReadList(initiatives=filtered_initiatives)


@router.post("/initiative/{initiative_id}/activity", response_model=s.ActivityRead)
async def create_activity(
    initiative_id: int,
    activity: s.ActivityCreate,
    request: Request,
    required_user=Depends(required_login_dep),
    initiative_manager: im.InitiativeManager = Depends(im.get_initiative_manager),
    activity_manager: am.ActivityManager = Depends(am.get_activity_manager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    initiative_db = await initiative_manager.min_load(initiative_id)
    auth.authorize(required_user, "create_activity", initiative_db, oso)
    activity_db = await activity_manager.create(
        activity, initiative_id, request=request
    )
    return auth.get_authorized_output_fields(required_user, "read", activity_db, oso)


@router.get(
    "/initiative/{initiative_id}/activity/{activity_id}",
    response_model=s.ActivityReadLinked,
    response_model_exclude_unset=True,
)
async def get_activity(
    initiative_id: int,
    activity_id: int,
    optional_user=Depends(optional_login_dep),
    activity_manager: am.ActivityManager = Depends(am.get_activity_manager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    activity_db = await activity_manager.detail_load(initiative_id, activity_id)
    auth.authorize(optional_user, "read", activity_db, oso)
    return auth.get_authorized_output_fields(optional_user, "read", activity_db, oso)


@router.patch(
    "/initiative/{initiative_id}/activity/{activity_id}",
    response_model=s.ActivityRead,
    response_model_exclude_unset=True,
)
async def update_activity(
    initiative_id: int,
    activity_id: int,
    activity: s.ActivityUpdate,
    request: Request,
    required_user=Depends(required_login_dep),
    activity_manager: am.ActivityManager = Depends(am.get_activity_manager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    activity_db = await activity_manager.min_load(initiative_id, activity_id)
    auth.authorize(required_user, "edit", activity_db, oso)
    edited_activity = await activity_manager.update(
        activity, activity_db, request=request
    )
    return auth.get_authorized_output_fields(
        required_user, "read", edited_activity, oso
    )


@router.patch(
    "/initiative/{initiative_id}/activity/{activity_id}/owners",
    response_model=s.UserReadList,
)
async def link_activity_owners(
    initiative_id: int,
    activity_id: int,
    activity: s.ActivityOwnersUpdate,
    request: Request,
    required_user=Depends(required_login_dep),
    activity_manager: am.ActivityManager = Depends(am.get_activity_manager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    activity_db = await activity_manager.detail_load(initiative_id, activity_id)
    auth.authorize(required_user, "edit", activity_db, oso)
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


@router.delete("/initiative/{initiative_id}/activity/{activity_id}")
async def delete_activity(
    initiative_id: int,
    activity_id: int,
    request: Request,
    required_user=Depends(required_login_dep),
    activity_manager: am.ActivityManager = Depends(am.get_activity_manager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    activity_db = await activity_manager.min_load(initiative_id, activity_id)
    auth.authorize(required_user, "delete", activity_db, oso)
    await activity_manager.delete(activity_db, request=request)
    return Response(status_code=204)


@router.patch(
    "/initiative/{initiative_id}/debit-cards",
    response_model=s.DebitCardReadList,
)
async def link_initiative_debit_cards(
    initiative_id: int,
    initiative: s.InitiativeDebitCardsUpdate,
    request: Request,
    required_user=Depends(required_login_dep),
    initiative_manager: im.InitiativeManager = Depends(im.get_initiative_manager),
    oso=Depends(auth.set_sqlalchemy_adapter),
):
    initiative_db = await initiative_manager.detail_load(initiative_id)
    auth.authorize(required_user, "edit", initiative_db, oso)
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


# ROUTES
# POST "/initiative/{initiative_id}/activity/{activity_id}/payment",
# PATCH "/initiative/{initiative_id}/activity/{activity_id}/payment/{payment_id}",
# DELETE "/initiative/{initiative_id}/activity/{activity_id}/payment/{payment_id}",
# GET "/initiative/{initiative_id}/activity/{activity_id}/payments"
# GET "/initiatives/aggregate-numbers"
# POST "/initiative/{initiative_id}/payment",
# PATCH "/initiative/{initiative_id}/payment/{payment_id}",
# DELETE "/initiative/{initiative_id}/payment/{payment_id}"
# GET "/initiative/{initiative_id}/payments"
# POST /debit-card,
# PATCH "/debit-card/{debit_card_id}",
# GET "/initiative/{initiative_id}/debit-cards"
# GET "/initiative/{initiative_id}/debit-cards/aggregate-numbers"
