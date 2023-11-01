from datetime import datetime, timedelta
from nordigen import NordigenClient
import os
import asyncio
from pydantic import BaseModel

lock = asyncio.Lock()

access_token: str | None = None
refresh_token: str | None = None
access_expires_at: datetime | None = None
refresh_expires_at: datetime | None = None


CLIENT = NordigenClient(
    secret_id=os.environ.get("GOCARDLESS_ID"),
    secret_key=os.environ.get("GOCARDLESS_KEY"),
)


def token_is_expired(token_expires_at: datetime):
    return datetime.now() > token_expires_at


async def refresh_tokens():
    global access_token
    global refresh_token
    global access_expires_at
    global refresh_expires_at
    async with lock:
        if not access_token or token_is_expired(access_expires_at):
            if refresh_token and not token_is_expired(refresh_expires_at):
                token_data = await CLIENT.exchange_token(refresh_token)
                access_token = token_data["access"]
                access_expires_at = datetime.now() + timedelta(
                    seconds=token_data["access_expires"]
                )
            else:
                token_data = await CLIENT.generate_token()
                access_token = token_data["access"]
                access_expires_at = datetime.now() + timedelta(
                    seconds=token_data["access_expires"]
                )
                refresh_token = token_data["refresh"]
                refresh_expires_at = datetime.now() + timedelta(
                    seconds=token_data["refresh_expires"]
                )
        CLIENT.token = access_token


async def get_nordigen_client():
    await refresh_tokens()
    return CLIENT


async def get_institutions():
    client = await get_nordigen_client()
    return await client.institution.get_institutions(country="NL")


class GocardlessInstitution(BaseModel):
    id: str
    name: str
    bic: str
    transaction_total_days: int
    countries: list[str]
    logo: str


class GoCardlessInstitutionList(BaseModel):
    institutions: list[GocardlessInstitution]

    @property
    def institution_ids(self):
        return [i.id for i in self.institutions]

    def get_transaction_total_days(self, institution_id: str):
        id_to_days = {i.id: i.transaction_total_days for i in self.institutions}
        return id_to_days[institution_id]


# Get information on all institutions once at app startup.
INSTITUTIONS = GoCardlessInstitutionList(institutions=asyncio.run(get_institutions()))
