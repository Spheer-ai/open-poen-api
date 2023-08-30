from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Request
from ..database import get_async_session
from ..schemas import ActivityCreate, ActivityUpdate
from ..models import (
    BankAccount,
    Payment,
    UserBankAccountRole,
    User,
    BankAccountRole,
    ReqStatus,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, and_, delete
from sqlalchemy.orm import selectinload
from .exc import EntityNotFound
from .exc import EntityAlreadyExists, EntityNotFound
from .base_manager import Manager
import asyncio
from ..gocardless import client
from nordigen import NordigenClient
from nordigen.types import Requisition


class PaymentManager(Manager):
    pass


def get_payment_manager(session: AsyncSession = Depends(get_async_session)):
    yield PaymentManager(session)
