import typer
from .database import engine, get_async_session_context, get_user_db_context
from .schemas_and_models import UserCreateWithPassword
from .gocardless import client, refresh_tokens
from .utils.utils import temp_password_generator
from .user_manager import get_user_manager_context
from fastapi_users.exceptions import UserAlreadyExists
from .schemas_and_models.models.entities import Role
import asyncio
from rich import print
from pydantic import EmailStr
from typing import Literal

app = typer.Typer()


async def async_add_user(
    email: EmailStr,
    superuser: bool,
    role: Literal["user", "financial", "admin"],
):
    try:
        async with get_async_session_context() as session:
            async with get_user_db_context(session) as user_db:
                async with get_user_manager_context(user_db) as user_manager:
                    user_schema = UserCreateWithPassword(
                        email=email,
                        is_superuser=superuser,
                        role=role,
                        password=temp_password_generator(16),
                    )
                    user = await user_manager.create(user_schema)
                    typer.echo(f"Added user with id {user.id}")
    except UserAlreadyExists:
        print(f"User {email} already exists")


@app.command()
def add_user(
    email: str,
    superuser: bool = False,
    role: str = "user",
):
    asyncio.run(async_add_user(email, superuser, role))


@app.command()
def list_agreements(limit: int = 100, offset: int = 0):
    asyncio.run(refresh_tokens())
    agreements = client.agreement.get_agreements(limit, offset)
    print(agreements)


@app.command()
def list_requisitions(limit: int = 100, offset: int = 0):
    asyncio.run(refresh_tokens())
    requisitions = client.requisition.get_requisitions(limit, offset)
    print(requisitions)


@app.command()
def list_transactions(account_id: str, date_from: str, date_to: str):
    asyncio.run(refresh_tokens())
    transactions = client.account_api(account_id).get_transactions(date_from, date_to)
    print(transactions)
