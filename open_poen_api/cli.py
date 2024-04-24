import typer
from .database import (
    get_async_session_context,
    get_user_db_context,
    create_db_and_tables,
    drop_all,
)
from .schemas import UserCreateWithPassword
from .gocardless import get_nordigen_client
from .utils.utils import temp_password_generator
from .managers import UserManager
from .gocardless.payments import get_gocardless_payments
from .utils.utils import create_media_container

# from fastapi_users.exceptions import UserAlreadyExists
from .exc import EntityAlreadyExists
import asyncio
from rich import print
from datetime import datetime

app = typer.Typer()


async def async_add_user(
    email: str,
    superuser: bool,
    role: str,
    password: str,
):
    if password == "random":
        password = temp_password_generator(16)
    try:
        async with get_async_session_context() as session:
            async with get_user_db_context(session) as user_db:
                user_manager = UserManager(user_db, session, None)
                user_schema = UserCreateWithPassword(
                    email=email,
                    is_superuser=superuser,
                    role=role,
                    password=password,
                )
                user = await user_manager.create(user_schema)
                typer.echo(f"Added user with id {user.id}")
    except EntityAlreadyExists:
        print(f"User {email} already exists")


@app.command()
def add_user(
    email: str,
    superuser: bool = False,
    role: str = "user",
    password: str = "random",
):
    asyncio.run(async_add_user(email, superuser, role, password))


async def async_add_superusers(emails: list[str], password: str):
    await asyncio.gather(
        *[async_add_user(email, True, "user", password) for email in emails]
    )


@app.command()
def add_superusers(
    emails: list[str],
    password: str = "random",
):
    asyncio.run(async_add_superusers(emails, password))


@app.command()
def reset_db():
    confirmation = typer.confirm(
        "Are you sure? This will remove all data from the database."
    )
    if confirmation:
        asyncio.run(create_db_and_tables())


@app.command()
def clear_db():
    confirmation = typer.confirm(
        "Are you sure? This will remove all data from the database."
    )
    if confirmation:
        asyncio.run(drop_all())


@app.command()
def retrieve_payments(requisition_id: int, date_from: str = ""):
    if date_from != "":
        try:
            parsed_date_from = datetime.strptime(date_from, "%Y-%m-%d")
        except ValueError:
            typer.echo("Invalid date format. Use YYYY-MM-DD.")
            raise typer.Abort()

    asyncio.run(get_gocardless_payments(requisition_id, parsed_date_from))


@app.command()
def retrieve_all_payments():
    asyncio.run(get_gocardless_payments())


@app.command()
def list_agreements(limit: int = 100, offset: int = 0):
    async def async_list_agreements(limit: int = 100, offset: int = 0):
        client = await get_nordigen_client()
        agreements = await client.agreement.get_agreements(limit, offset)
        print(agreements)

    asyncio.run(async_list_agreements(limit, offset))


@app.command()
def delete_all_agreements(limit: int = 100, offset: int = 0):
    async def async_delete_all_agreements(limit: int = 100, offset: int = 0):
        client = await get_nordigen_client()
        agreements = await client.agreement.get_agreements(limit, offset)
        for a in agreements["results"]:
            await client.agreement.delete_agreement(a["id"])

    asyncio.run(async_delete_all_agreements(limit, offset))


@app.command()
def list_requisitions(limit: int = 100, offset: int = 0):
    async def async_list_requisitions(limit: int = 100, offset: int = 0):
        client = await get_nordigen_client()
        requisitions = await client.requisition.get_requisitions(limit, offset)
        print(requisitions)

    asyncio.run(async_list_requisitions(limit, offset))


@app.command()
def delete_all_requisitions(limit: int = 100, offset: int = 0):
    async def async_delete_all_requisitions(limit: int = 100, offset: int = 0):
        client = await get_nordigen_client()
        requisitions = await client.requisition.get_requisitions(limit, offset)
        for r in requisitions["results"]:
            await client.requisition.delete_requisition(r["id"])

    asyncio.run(async_delete_all_requisitions(limit, offset))


@app.command()
def list_transactions(account_id: str, date_from: str, date_to: str):
    async def async_list_transactions(account_id: str, date_from: str, date_to: str):
        client = await get_nordigen_client()
        transactions = await client.account_api(account_id).get_transactions(
            date_from, date_to
        )
        print(transactions)

    asyncio.run(async_list_transactions(account_id, date_from, date_to))


@app.command()
def list_institutions(country: str):
    async def async_list_institutions(country: str):
        client = await get_nordigen_client()
        institutions = await client.institution.get_institutions(country)
        print(institutions)

    asyncio.run(async_list_institutions(country))


@app.command()
def create_local_media_container():
    """Azurite needs the same media container to be created every time its container is built.
    The environments on Azure: test, acceptance and production, have the media container created
    by Terraform."""
    asyncio.run(create_media_container())
