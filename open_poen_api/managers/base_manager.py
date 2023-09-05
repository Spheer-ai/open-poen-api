from .base_manager_ex_current_user import BaseManagerExCurrentUser
from fastapi import Depends
from ..database import get_async_session, AsyncSession
from .user_manager import optional_login
from ..models import User


class BaseManager(BaseManagerExCurrentUser):
    def __init__(
        self,
        session: AsyncSession = Depends(get_async_session),
        current_user: User | None = Depends(optional_login),
    ):
        super().__init__(session, current_user)
