from .models import User, Base
from typing import AsyncGenerator
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi import Depends
import contextlib

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os

# TODO: Configure this with environment variables.
async_engine = create_async_engine(os.environ["ASYNC_DATABASE_URL"])
async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)

sync_engine = create_engine(os.environ["SYNC_DATABASE_URL"])
sync_session_maker = sessionmaker(sync_engine, expire_on_commit=False)


async def create_db_and_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def drop_all():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_sync_session():
    with sync_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)


get_async_session_context = contextlib.asynccontextmanager(get_async_session)
get_user_db_context = contextlib.asynccontextmanager(get_user_db)
