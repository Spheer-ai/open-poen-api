import json
import requests
import os
from pydantic import BaseModel

MAX_REQ_VALIDITY = 90


class Token(BaseModel):
    access: str
    access_expires: int
    refresh: str
    refresh_expires: int


class Institution(BaseModel):
    id: str
    name: str
    bic: str | None
    transaction_total_days: int | None
    countries: list[str]
    logo: str


def create_new_token() -> Token:
    url = "https://bankaccountdata.gocardless.com/api/v2/token/new/"
    headers = {"accept": "application/json", "Content-Type": "application/json"}
    data = {
        "secret_id": os.environ.get("GOCARDLESS_ID"),
        "secret_key": os.environ.get("GOCARDLESS_KEY"),
    }
    r = requests.post(url, headers=headers, data=json.dumps(data))
    r.raise_for_status()
    token = Token.parse_obj(r.json())
    return token


def get_institutions(access_token: str, country: str = "nl") -> list[Institution]:
    url = (
        f"https://bankaccountdata.gocardless.com/api/v2/institutions/?country={country}"
    )
    headers = {"accept": "application/json", "Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    institutions = [Institution.parse_obj(i) for i in response.json()]
    return institutions


def create_new_agreement(
    access_token: str,
    institution: Institution,
    max_historical_days: int = 720,
    access_scope: list[str] = ["balances", "details", "transactions"],
) -> dict:
    if (
        institution.transaction_total_days is not None
        and max_historical_days > institution.transaction_total_days
    ):
        raise ValueError(
            f"Historical days to request is {max_historical_days} but institution allows {institution.transaction_total_days}."
        )
    url = "https://bankaccountdata.gocardless.com/api/v2/agreements/enduser/"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    data = {
        "institution_id": institution.id,
        "max_historical_days": max_historical_days,
        "access_valid_for_days": MAX_REQ_VALIDITY,
        "access_scope": access_scope,
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    response.raise_for_status()
    return response.json()
