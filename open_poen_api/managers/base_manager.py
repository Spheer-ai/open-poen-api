from fastapi import Depends
from ..database import get_async_session, AsyncSession
from .user_manager import optional_login
from ..models import User
from .base_manager_ex_current_user import BaseCRUD, BaseLoad


class BaseManager:
    def __init__(
        self,
        session: AsyncSession = Depends(get_async_session),
        current_user: User | None = Depends(optional_login),
    ):
        self.crud = BaseCRUD(session, current_user)
        self.load = BaseLoad(session)
