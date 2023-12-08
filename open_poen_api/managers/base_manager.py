from fastapi import Depends
from ..database import get_async_session, AsyncSession
from .user_manager.user_manager_ex_current_user import optional_login
from ..models import User
from .bases import BaseLogger, BaseCRUD, BaseLoad


class BaseManager:
    def __init__(
        self,
        session: AsyncSession = Depends(get_async_session),
        current_user: User | None = Depends(optional_login),
    ):
        self.logger = BaseLogger(current_user)
        self.crud = BaseCRUD(session, current_user)
        self.load = BaseLoad(session)
        self.session = session
        self.current_user = current_user
