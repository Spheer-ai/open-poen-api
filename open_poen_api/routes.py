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
from sqlalchemy.orm.exc import FlushError
from dotenv import load_dotenv
import os

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
@router.post("/initiative", response_model=m.Initiative)
async def create_initiative(
    initiative: m.InitiativeCreateIn,
    session: Session = Depends(get_session),
):
    # NOTE: THIS WORKS AND CREATES A NEW USER
    # u = m.User(email="testje@gmail.com", hashed_password="kdjflkdjf")
    # ni = m.Initiative(name="testje", initiative_owners=[u])
    # session.add(ni)
    # session.commit()

    try:
        users = session.exec(
            select(m.User).where(col(m.User.email).in_([initiative.initiative_owners]))
        ).all()
        if len(users) != len(initiative.initiative_owners):
            raise HTTPException(
                status_code=400,
                detail="One or more email addresses do not have associated users",
            )
        new_initiative = m.Initiative(name=initiative.name, initiative_owners=users)
        session.add(new_initiative)
        session.commit()
        return new_initiative
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Initiative creation failed")


@router.put("/initiative/{initiative_id}")
async def root(initiative_id: int):
    return {"name": "Buurtproject", "created_at": "2022-6-6"}


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
    new_user.initiatives = session.exec(
        select(m.Initiative).where(col(m.Initiative.id).in_(user.initiative_ids))
    ).all()
    try:
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return new_user
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Email address already registered")
    except FlushError:
        session.rollback()
        raise HTTPException(
            status_code=404, detail="One or more initiatves do not exist"
        )


@router.put("/user/{user_id}")
async def update_user(
    user_id: int,
    user: m.UserUpdateIn,
    session: Session = Depends(get_session),
    response_model=m.UserOut,
):
    user_db = session.get(m.User, user_id)
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")
    if not user_db.id == user.id:
        raise HTTPException(
            status_code=400, detail="Query and body parameters for id are incongruent"
        )
    user_db.email = user.email
    user_db.first_name = user.first_name
    user_db.last_name = user.last_name
    session.commit()
    return user


@router.delete("/user/{user_id}")
async def delete_user(
    user_id: int, session: Session = Depends(get_session), response_model=Response
):
    user = session.get(m.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    session.delete(user)
    session.commit()
    return Response(status_code=204)


TSource = TypeVar("TSource", bound=SQLModel)
TTarget = TypeVar("TTarget", bound=SQLModel)


def convert_instances(
    source_model: Type[TSource], target_model: Type[TTarget], instances: List[TSource]
) -> List[TTarget]:
    subset_instances = []

    for instance in instances:
        subset_instance = {}
        for column in get_type_hints(target_model).keys():
            if hasattr(instance, column):
                subset_instance[column] = getattr(instance, column)
        subset_instances.append(target_model(**subset_instance))

    return subset_instances


# @router.get("/users", response_model=m.TempUser)
# def get_users(session: Session = Depends(get_session)):
#     users = session.exec(select(m.User)).all()
#     # return convert_instances(m.User, m.UserUpdate, users)
#     # return [m.UserUpdate.from_orm(i) for i in users]
#     return {"users": users}


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
