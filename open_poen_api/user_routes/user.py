from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)

from fastapi_users.exceptions import UserAlreadyExists
from ..database import get_async_session
from .. import schemas_and_models as s
from .. import authorization as auth
from ..utils.utils import (
    temp_password_generator,
)
import os
from requests.exceptions import RequestException
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select


DOMAIN_NAME = os.environ.get("DOMAIN_NAME")


user_router = APIRouter()


@user_router.post("/user", response_model=s.UserRead)
async def create_user(
    user: s.UserCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    current_user=Depends(auth.fastapi_users.current_user(optional=True)),
    user_manager: auth.UserManager = Depends(auth.get_user_manager),
):
    user_with_password = s.UserCreateWithPassword(
        **user.dict(), password=temp_password_generator(16)
    )
    try:
        new_user = await user_manager.create(user_with_password, request=request)
    except UserAlreadyExists:
        raise HTTPException(status_code=400, detail="Email address already registered")
    session.refresh(new_user)
    return s.UserRead.from_orm(new_user)


# @router.patch(
#     "/user/{user_id}",
#     response_model=le.UserOutputAdminWithLinkedEntities,
#     response_model_exclude_unset=True,
# )
# @router.patch("/user/{user_id}")
# async def update_user(
#     user_id: int,
#     user: s.UserUpdateAdmin,
#     session: AsyncSession = Depends(get_async_session),
#     auth_levels: list[auth.AuthLevel] = Depends(
#         auth.get_user_auth_levels(requires_login=True)
#     ),
# ):
#     user_db = session.get(ent.User, user_id)
#     if not user_db:
#         raise HTTPException(status_code=404, detail="User not found")

#     auth.validate_input_schema(
#         unified_input_schema=user,
#         parse_schemas=[
#             (auth.AuthLevel.ADMIN, s.UserUpdateAdmin),
#             (auth.AuthLevel.USER_OWNER, s.UserUpdateUserOwner),
#         ],
#         auth_levels=auth_levels,
#     )

#     fields = get_fields_dict(user.dict(exclude_unset=True))
#     for key, value in fields.items():
#         setattr(user_db, key, value)
#     if user.initiative_ids is not None:
#         user_db.initiatives = get_entities_by_ids(
#             session, ent.Initiative, user.initiative_ids
#         )
#     if user.activity_ids is not None:
#         user_db.activities = get_entities_by_ids(
#             session, ent.Activity, user.activity_ids
#         )
#     try:
#         session.add(user_db)
#         session.commit()
#         session.refresh(user_db)
#         return auth.validate_output_schema(
#             user_db,
#             parse_schemas=[
#                 (auth.AuthLevel.ADMIN, le.UserOutputAdminWithLinkedEntities),
#                 (auth.AuthLevel.USER_OWNER, le.UserOutputUserOwnerWithLinkedEntities),
#             ],
#             auth_levels=auth_levels,
#         )
#     except IntegrityError:
#         session.rollback()
#         raise HTTPException(status_code=400, detail="Email address already registered")


# @router.delete("/user/{user_id}")
# async def delete_user(
#     user_id: int,
#     requires_admin=Depends(auth.requires_admin),
#     session: AsyncSession = Depends(get_async_session),
# ):
#     # TODO: Make soft delete.
#     user = session.get(ent.User, user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")

#     session.delete(user)
#     session.commit()
#     return Response(status_code=204)


# @router.get(
#     "/users", response_model=s.UserOutputAdminList, response_model_exclude_unset=True
# )
# def get_users(
#     session: AsyncSession = Depends(get_async_session),
#     auth_levels: list[auth.AuthLevel] = Depends(
#         auth.get_user_auth_levels(requires_login=True)
#     ),
# ):
#     # TODO: Enable searching by email.
#     # TODO: pagination.
#     users = session.exec(select(ent.User)).all()
#     parsed_users = auth.validate_output_schema(
#         users,
#         parse_schemas=[
#             (auth.AuthLevel.ADMIN, s.UserOutputAdminList),
#             (auth.AuthLevel.USER, s.UserOutputUserList),
#         ],
#         auth_levels=auth_levels,
#         seq_key="users",
#     )
#     return parsed_users


# # # BNG
# @router.get(
#     "/users/{user_id}/bng-initiate",
#     response_class=RedirectResponse,
# )
# async def bng_initiate(
#     user_id: int,
#     bng: s.BNGCreateAdmin,
#     requires_user_owner=Depends(auth.requires_user_owner),
#     requires_admin=Depends(auth.requires_admin),
#     session: AsyncSession = Depends(get_async_session),
#     requester_ip: str = Depends(get_requester_ip),
# ):
#     user = session.get(ent.User, user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")

#     existing_bng = session.exec(select(ent.BNG)).first()
#     if existing_bng:
#         raise HTTPException(
#             status_code=400,
#             detail=f"A BNG Account with IBAN {existing_bng.iban} is already linked.",
#         )
#     try:
#         consent_id, oauth_url = create_consent(
#             iban=bng.iban,
#             valid_until=bng.expires_on,
#             redirect_url=f"https://{DOMAIN_NAME}/users/{user_id}/bng-callback",
#             requester_ip=requester_ip,
#         )
#     except RequestException as e:
#         raise HTTPException(
#             status_code=500, detail="Error in request for consent to BNG."
#         )
#     token = jwt.encode(
#         {
#             "user_id": user_id,
#             "iban": bng.iban,
#             "bank_name": "BNG",
#             "exp": time() + 1800,
#             "consent_id": consent_id,
#         },
#         auth.SECRET_KEY,
#         auth.ALGORITHM,
#     ).decode("utf-8")
#     url_to_return = oauth_url.format(token)
#     # TODO: Don't return a redirect, but some json with the link.
#     return RedirectResponse(url=url_to_return)


# @router.post("/users/{user_id}/bng-callback", response_model=s.BNGOutputAdmin)
# async def bng_callback(
#     user_id: int,
#     background_tasks: BackgroundTasks,
#     code: str = Query(),
#     state: str = Query(),
#     session: AsyncSession = Depends(get_async_session),
# ):
#     try:
#         payload = jwt.decode(state, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
#     except ExpiredSignatureError:
#         raise HTTPException(status_code=401, detail="JWT token expired")
#     except JWTError:
#         raise HTTPException(status_code=401, detail="Could not validate JWT token")

#     try:
#         response = retrieve_access_token(code, redirect_url="")
#     except RequestException as e:
#         raise HTTPException(
#             status_code=500, detail="Error in retrieval of access token from BNG"
#         )

#     access_token, expires_in = response["access_token"], response["expires_in"]
#     expires_on = datetime.now(pytz.timezone("Europe/Amsterdam")) + timedelta(
#         seconds=int(expires_in)
#     )
#     new_bng_account = ent.BNG(
#         iban=payload["iban"],
#         expires_on=expires_on,
#         user_id=payload["user_id"],
#         consent_id=payload["consent_id"],
#         access_token=access_token,
#         last_import_on=None,
#     )
#     session.add(new_bng_account)
#     session.commit()
#     session.refresh(new_bng_account)
#     background_tasks.add_task(get_bng_payments, session)
#     # Here we should redirect the user back to a route in the SPA.
#     return new_bng_account


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
