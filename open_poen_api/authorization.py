from sqlmodel import Session, select, SQLModel
from fastapi import Depends, HTTPException, status
from .database import get_session
from . import models as m
from typing import Annotated, Type, Sequence
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from enum import Enum
from pydantic import BaseModel, ValidationError


SECRET_KEY = "bladiebla"
ALGORITHM = "HS256"
OAUTH2_SCHEME = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")


def authenticate_user(email: str, password: str, session: Session):
    user = session.exec(select(m.User).where(m.User.email == email)).first()
    if not user:
        return False
    if not PWD_CONTEXT.verify(password, user.hashed_password):
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


def get_requester(
    token: Annotated[str | None, Depends(OAUTH2_SCHEME)],
    session: Session = Depends(get_session),
) -> m.User | None:
    """Gets the User instance of the requester, or returns None if the requester
    gives no credentials."""
    if token is None:
        return None
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = session.exec(select(m.User).where(m.User.email == email)).first()
    if user is None:
        raise credentials_exception
    if not user.active:
        raise HTTPException(status_code=403, detail="User is inactive")
    return user


def get_logged_in_user(requester: Annotated[m.User | None, Depends(get_requester)]):
    if requester is None:
        raise HTTPException(status_code=401, detail="Requires login")
    else:
        return requester


class AuthLevel(str, Enum):
    """
    Enum representing various authorization levels in the Open Poen application:

    - GUEST: Any requester not validating with credentials.
    - USER: A standard user of Open Poen.
    - USER_OWNER: A user requesting data about an entity related to their own user account.
    - ACTIVITY_OWNER: A user requesting data about an entity related to an activity they are linked to.
    - INITIATIVE_OWNER: A user requesting data about an entity related to an initiative they are linked to.
    - FINANCIAL: A user who is also a civil servant, with special permissions for entities related to an initiative they are linked to.
    - ADMIN: A user with full rights.
    """

    GUEST = "guest"
    USER = "user"
    USER_OWNER = "user_owner"
    ACTIVITY_OWNER = "activity_owner"
    INITIATIVE_OWNER = "initiative_owner"
    FINANCIAL = "financial"
    ADMIN = "admin"

    def __str__(self):
        return self.value


def get_authorization_level(
    requester: Annotated[
        m.User | None,
        Depends(get_requester),
    ],
    user_id: int | None = None,
    initiative_id: int | None = None,
    activity_id: int | None = None,
) -> list[AuthLevel]:
    if requester is None:
        return [AuthLevel.GUEST]
    auth_levels = [AuthLevel.USER]
    if user_id is not None and requester.id == user_id:
        auth_levels.append(AuthLevel.USER_OWNER)
    if initiative_id is not None and initiative_id in map(
        lambda x: x.id, requester.initiatives
    ):
        auth_levels.append(AuthLevel.INITIATIVE_OWNER)
        if requester.role == m.Role.FINANCIAL:
            auth_levels.append(AuthLevel.FINANCIAL)
    if activity_id is not None and activity_id in map(
        lambda x: x.id, requester.activities
    ):
        auth_levels.append(AuthLevel.ACTIVITY_OWNER)
    if requester.role == m.Role.ADMIN:
        auth_levels.append(AuthLevel.ADMIN)
    return auth_levels


def requires_admin(logged_in_user: Annotated[m.User, Depends(get_logged_in_user)]):
    if not logged_in_user.role == m.Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin authorization required")


def requires_login(logged_in_user: Annotated[m.User, Depends(get_logged_in_user)]):
    pass


def validate_input_schema(
    unified_input_schema: BaseModel,
    parse_schemas: list[tuple[AuthLevel, Type[BaseModel]]],
    auth_levels: list[AuthLevel],
):
    # TODO: Document this / make it more readable.
    for level, schema in parse_schemas:
        if level in auth_levels:
            try:
                schema(**unified_input_schema.dict(exclude_unset=True))
                return
            except ValidationError:
                raise HTTPException(
                    status_code=403,
                    detail=f"Unauthorized - Invalid data for level {str(level)}",
                )
    raise HTTPException(
        status_code=403,
        detail=f"Unauthorized - Invalid authentication level(s) {[str(x) for x in auth_levels]}",
    )


def validate_output_schema(
    output_schema_instance: SQLModel | Sequence[SQLModel],
    parse_schemas: list[tuple[AuthLevel, Type[BaseModel]]],
    auth_levels: list[AuthLevel],
    seq_key: str | None = None,
):
    for level, schema in parse_schemas:
        if level in auth_levels:
            if seq_key is None:
                return schema.from_orm(output_schema_instance)
            else:
                return schema(**{seq_key: output_schema_instance})
    raise HTTPException(status_code=500)
