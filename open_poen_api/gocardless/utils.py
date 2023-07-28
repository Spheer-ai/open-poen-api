from datetime import datetime, timedelta
from nordigen import NordigenClient
import os
import asyncio
from ..utils.load_env import load_env_vars

load_env_vars()

lock = asyncio.Lock()

access_token: str | None = None
refresh_token: str | None = None
access_expires_at: datetime | None = None
refresh_expires_at: datetime | None = None


client = NordigenClient(
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
                token_data = client.exchange_token(refresh_token)
                access_token = token_data["access"]
                access_expires_at = datetime.now() + timedelta(
                    seconds=token_data["access_expires"]
                )
            else:
                token_data = client.generate_token()
                access_token = token_data["access"]
                access_expires_at = datetime.now() + timedelta(
                    seconds=token_data["access_expires"]
                )
                refresh_token = token_data["refresh"]
                refresh_expires_at = datetime.now() + timedelta(
                    seconds=token_data["refresh_expires"]
                )
        client.token = access_token


# TODO: This should probably not be hard coded, but retrieved dynamically.
INSTITUTION_ID_TO_TRANSACTION_TOTAL_DAYS = {
    "ABNAMRO_ABNANL2A": 540,
    "ASN_BANK_ASNBNL21": 730,
    "ING_INGBNL2A": 730,
    "KNAB_KNABNL2H": 730,
    "RABOBANK_RABONL2U": 730,
    "REGIOBANK_RBRBNL21": 730,
    "SNS_BANK_SNSBNL2A": 730,
    "TRIODOS_TRIONL2U": 730,
}
