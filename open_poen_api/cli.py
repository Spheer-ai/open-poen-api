import typer
from .database import engine, async_session_maker
from .schemas_and_models.models.entities import User
from .gocardless import client, refresh_tokens
import asyncio
from rich import print
from pydantic import EmailStr

app = typer.Typer()


async def async_add_user(
    email: EmailStr, is_superuser: bool = False, password: str = "bla"
):
    # TODO: Share functionality for creating a user with the route.
    # TODO: We'll need this to add the first Admin.
    random_user = User()
    async with async_session_maker() as session:
        session.add(random_user)
        await session.commit()
        await session.refresh(random_user)
        typer.echo(f"Added user with id {random_user.id}")


@app.command()
def add_user():
    asyncio.run(async_add_user())


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
