from sqlmodel import Session, select, SQLModel, col
from fastapi import APIRouter, Depends, HTTPException, status, Response
from .database import get_session
from . import models as m
from typing import Annotated, List, get_type_hints, TypeVar, Type, Tuple
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from pydantic import BaseModel
import string
import random
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
import os
from .utils import get_entities_by_ids

load_dotenv()

DEBUG = os.getenv("DEBUG") == "true"


router = APIRouter()


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "bladiebla"
ALGORITHM = "HS256"


class Token(BaseModel):
    access_token: str
    token_type: str


def authenticate_user(email: str, password: str, session: Session):
    user = session.query(m.User).filter(m.User.email == email).first()
    if not user:
        return False
    if not pwd_context.verify(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Session = Depends(get_session),
):
    user = authenticate_user(form_data.username, form_data.password, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=15)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ACTIVITY
# @router.post("/initiative/{initiative_id}/activity")
# async def root(
#     initiative_id: int,
#     activity: m.ActivityBase,
#     session: Session = Depends(get_session),
# ):
#     return activity


@router.put("/initiative/{initiative_id}/activity/{activity_id}")
async def root(initiative_id: int, activity_id: int):
    return {"name": "Eerste Activiteit"}


@router.delete("/initiative/{initiative_id}/activity/{activity_id}")
async def root(initiative_id: int, activity_id: int):
    return {"name": "Eerste Activiteit"}


@router.get("/initiative/{initiative_id}/activity/{activity_id}/users")
async def root(initiative_id: int, activity_id: int):
    return [
        {"first_name": "Mark", "last_name": "de Wijk"},
        {"first_name": "Jamal", "last_name": "Vleij"},
    ]


# ACTIVITY - PAYMENT
@router.post("/initiative/{initiative_id}/activity/{activity_id}/payment")
async def root(initiative_id: int, activity_id: int):
    return {"amount": 10.01, "debitor": "Mark de Wijk"}


@router.put("/initiative/{initiative_id}/activity/{activity_id}/payment/{payment_id}")
async def root(initiative_id: int, activity_id: int, payment_id: int):
    return {"amount": 10.01, "debitor": "Mark de Wijk"}


@router.delete(
    "/initiative/{initiative_id}/activity/{activity_id}/payment/{payment_id}"
)
async def root(initiative_id: int, activity_id: int, payment_id: int):
    return {"status_code": 204, "content": "Succesfully deleted."}


@router.get("/initiative/{initiative_id}/activity/{activity_id}/payments")
async def root(initiative_id: int, activity_id: int):
    return {"status_code": 200, "content": "to implement"}


# INITIATIVE
@router.post("/initiative", response_model=m.InitiativeOutWithOwners)
async def create_initiative(
    initiative: m.InitiativeCreateIn,
    session: Session = Depends(get_session),
):
    fields = get_fields_dict(initiative)
    new_initiative = m.Initiative(**fields)
    if initiative.initiative_owner_ids is not None:
        new_initiative.initiative_owners = get_entities_by_ids(
            session, m.User, initiative.initiative_owner_ids
        )
    try:
        session.add(new_initiative)
        session.commit()
        session.refresh(new_initiative)
        return new_initiative
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Name already registered")


@router.put("/initiative/{initiative_id}", response_model=m.InitiativeOutWithOwners)
async def update_initiative(
    initiative_id: int,
    initiative: m.InitiativeUpdateIn,
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
    try:
        session.add(initiative_db)
        session.commit()
        session.refresh(initiative_db)
        return initiative_db
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Name already registered")


@router.delete("/initiative/{initiative_id}")
async def root(initiative_id: int):
    return {"status_code": 204, "content": "Succesfully deleted."}


@router.get("/initiatives")
async def root():
    return [
        {"name": "Buurtproject", "created_at": "2022-6-6"},
        {"name": "Smoelenboek", "created_at": "2022-2-22"},
    ]


@router.get("/initiatives/aggregate-numbers")
async def root():
    # TODO: Merge into /initiatives?
    # NOTE: Can't merge, because /initiatives will be paginated.
    return {"total_spent": 100, "total_earned": 100, "initiative_count": 22}


@router.get("/initiative/{initiative_id}/users")
async def root(initiative_id: int):
    return [
        {"first_name": "Mark", "last_name": "de Wijk"},
        {"first_name": "Jamal", "last_name": "Vleij"},
    ]


@router.get("/initiative/{initiative_id}/activities")
async def root(initiative_id: int):
    return [
        {"name": "Eerste Activiteit"},
        {"name": "Tweede Activiteit"},
    ]


# INITIATIVE - PAYMENT
@router.post("/initiative/{initiative_id}/payment")
async def root(initiative_id: int):
    return {"amount": 10.01, "debitor": "Mark de Wijk"}


@router.put("/initiative/{initiative_id}/payment/{payment_id}")
async def root(initiative_id: int, payment_id: int):
    return {"amount": 10.01, "debitor": "Mark de Wijk"}


@router.delete("/initiative/{initiative_id}/payment/{payment_id}")
async def root(initiative_id: int, payment_id: int):
    return {"status_code": 204, "content": "Succesfully deleted."}


@router.get("/initiative/{initiative_id}/payments")
async def root(initiative_id: int):
    return [
        {"amount": 10.01, "debitor": "Mark de Wijk"},
        {"amount": 9.01, "debitor": "Jamal Vleij"},
    ]


# INITIATIVE - DEBIT CARD
@router.post("/initiative/{initiative_id}/debit-card")
async def root(initiative_id: int):
    return {"card_number": 12345678, "created_at": "2011-8-1"}


@router.put("/initiative/{initiative_id}/debit-card/{debit_card_id}")
async def root(initiative_id: int, debit_card_id: int):
    # Use this to (de)couple a debit card from/to an initiative.
    return {"card_number": 12345678, "created_at": "2011-8-1"}


@router.get("/initiative/{initiative_id}/debit-cards")
async def root(initiative_id: int):
    return [
        {"card_number": 12345678, "created_at": "2011-8-1"},
        {"card_number": 12345679, "created_at": "2011-8-1"},
    ]


@router.get("/initiative/{initiative_id}/debit-cards/aggregate-numbers")
async def root(initiative_id: int):
    return [
        {"card_number": 12345678, "received": 2000, "spent": 199},
        {"card_number": 12345679, "received": 0, "spent": 0},
    ]


def temp_password_generator(
    size: int = 10, chars=string.ascii_uppercase + string.digits
) -> str:
    if not DEBUG:
        return "".join(random.choice(chars) for _ in range(size))
    else:
        return "DEBUG_PASSWORD"


def get_fields_dict(model: SQLModel) -> dict:
    """An input schema can have ids of entities for which we want to establish
    a relationship. Those we process separately, so we filter those out here."""
    fields_dict = {}
    for key, value in model.dict().items():
        if not key.endswith("_ids"):
            fields_dict[key] = value
    return fields_dict


# USER
@router.post("/user", response_model=m.UserOutWithInitiatives)
async def create_user(
    user: m.UserCreateIn,
    session: Session = Depends(get_session),
):
    # TODO: Send an email with the temporary password. Otherwise
    # The user isn't notified and he can't login!
    temp_password = temp_password_generator()
    fields = get_fields_dict(user)
    new_user = m.User(**fields, hashed_password=pwd_context.hash(temp_password))
    if user.initiative_ids is not None:
        new_user.initiatives = get_entities_by_ids(
            session, m.Initiative, user.initiative_ids
        )
    try:
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return new_user
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Email address already registered")


@router.put("/user/{user_id}", response_model=m.UserOutWithInitiatives)
async def update_user(
    user_id: int,
    user: m.UserUpdateIn,
    session: Session = Depends(get_session),
):
    user_db = session.get(m.User, user_id)
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")
    fields = get_fields_dict(user)
    for key, value in fields.items():
        setattr(user_db, key, value)
    if user.initiative_ids is not None:
        user_db.initiatives = get_entities_by_ids(
            session, m.Initiative, user.initiative_ids
        )
    try:
        session.add(user_db)
        session.commit()
        session.refresh(user_db)
        return user_db
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Email address already registered")


@router.delete("/user/{user_id}")
async def delete_user(user_id: int, session: Session = Depends(get_session)):
    user = session.get(m.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    session.delete(user)
    session.commit()
    return Response(status_code=204)


@router.get("/users", response_model=m.UserOutList)
def get_users(session: Session = Depends(get_session)):
    # TODO: Enable searching by email.
    users = session.exec(select(m.User)).all()
    return {"users": users}


# FUNDER
@router.post("/funder")
async def root():
    # If we continue linking to initiatives, we need to add such a query param.
    return {"name": "Gemeente Amsterdam", "created_at": "2022-4-1"}


@router.put("/funder/{funder_id}")
async def root(funder_id: int):
    return {"name": "Gemeente Amsterdam", "created_at": "2022-4-1"}


@router.delete("/funder/{funder_id}")
async def root(funder_id: int):
    return {"status_code": 204, "content": "Succesfully deleted."}


@router.get("/funders")
async def root():
    # If we continue linking to initiatives, we need to add such a query param.
    return [
        {"name": "Gemeente Amsterdam", "created_at": "2022-4-1"},
        {"name": "Stichting Leergeld", "created_at": "2022-1-1"},
    ]


# BNG
@router.post("/bng-connection")
async def root():
    # Should accept IBAN and only available to admins.
    return {"IBAN": "NL32INGB00039845938"}


@router.delete("/bng-connection")
async def root():
    return {"status_code": 204, "content": "Succesfully deleted."}


@router.get("/bng-connection")
async def root():
    # Only available to admins.
    return {"IBAN": "NL32INGB00039845938"}


@router.get("/bng-connection/status")
async def root():
    return {
        "present": True,
        "online": True,
        "days_left": 33,
        "last_sync": "2022-12-1, 17:53",
    }
