import json
import uuid
import requests
from wsgiref.handlers import format_date_time
from datetime import datetime, date
from time import mktime
import hashlib
import base64
from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA
from urllib.parse import urlparse
from urllib.parse import urlencode
import os

URI_FORMAT = os.environ.get("BNG_URI_FORMAT")
CLIENT_ID = str(os.environ.get("BNG_CLIENT_ID"))
KEYID_FDN = os.environ.get("BNG_KEYID_FDN")
TLS_CERTS = (
    str(os.environ.get("BNG_TLS_CER")),
    str(os.environ.get("BNG_TLS_KEY")),
)
SIGNING_CERTS = (os.environ.get("BNG_SIGN_CER"), os.environ.get("BNG_SIGN_KEY"))

API_URL_PREFIX = f"https://api.xs2a{URI_FORMAT}.bngbank.nl/api/v1/"
OAUTH_URL_PREFIX = (
    f"https://api.xs2a{URI_FORMAT}.bngbank.nl/authorise?response_type=code&"
)
ACCESS_TOKEN_URL = f"https://api.xs2a{URI_FORMAT}.bngbank.nl/token"


def get_current_rfc_1123_date():
    now = datetime.now()
    stamp = mktime(now.timetuple())
    return format_date_time(stamp)


def get_digest(body):
    hash = hashlib.sha256()
    hash.update(body.encode("utf-8"))
    digest_in_bytes = hash.digest()
    digest_in_base64 = base64.b64encode(digest_in_bytes)
    return "SHA-256=" + digest_in_base64.decode("utf-8")


def get_signature(method, headers):
    signature_header_names = ["request-target", "Date", "Digest", "X-Request-ID"]
    headers = {k: v for k, v in headers.items() if k in signature_header_names}
    headers = {
        "(request-target)" if k == "request-target" else k.lower(): v
        for k, v in headers.items()
    }
    path = urlparse(headers["(request-target)"]).path
    tail = headers["(request-target)"].split(path)[-1]
    headers["(request-target)"] = method + " " + path + tail

    signing_string = "\n".join([k + ": " + v for k, v in headers.items()])
    signature_headers = " ".join(headers.keys())

    digest = SHA256.new()
    digest.update(bytes(signing_string, encoding="utf-8"))

    with open(SIGNING_CERTS[1], "r") as file:
        private_key = RSA.importKey(file.read())

    signer = PKCS1_v1_5.new(private_key)
    signature = base64.b64encode(signer.sign(digest))

    return ",".join(
        [
            KEYID_FDN,
            'algorithm="sha256RSA"',
            'headers="' + signature_headers + '"',
            'signature="' + signature.decode("utf-8") + '"',
        ]
    )


def get_certificate():
    with open(SIGNING_CERTS[0], "r") as file:
        data = file.read().replace("\n", "")
    return data


def make_headers(
    method: str,
    url: str,
    request_id: str,
    body: str,
    psu_ip_address: str,
    content_type: str = "application/json",
    extra_headers: dict[str, str] = {},
):
    headers = {
        **extra_headers,
        "request-target": url,
        "Accept": "application/json",
        "Content-Type": content_type,
        "Date": get_current_rfc_1123_date(),
        "Digest": get_digest(body),
        "X-Request-ID": request_id,
        "PSU-IP-Address": psu_ip_address,
    }
    return {
        **headers,
        "Signature": get_signature(method, headers),
        "TPP-Signature-Certificate": get_certificate(),
    }


def create_consent(
    iban: str, valid_until: date, redirect_url: str, requester_ip: str = ""
) -> tuple[str, str]:
    body = {
        "access": {
            "accounts": [{"iban": iban, "currency": "EUR"}],
            "balances": [{"iban": iban, "currency": "EUR"}],
            "transactions": [{"iban": iban, "currency": "EUR"}],
            "availableAccounts": None,
            "availableAccountsWithBalances": None,
            "allPsd2": None,
        },
        "combinedServiceIndicator": False,
        "recurringIndicator": True,
        "validUntil": valid_until.strftime("%Y-%m-%d"),
        "frequencyPerDay": 4,
    }
    json_body = json.dumps(body)
    url = f"{API_URL_PREFIX}consents"
    request_id = str(uuid.uuid4())
    headers = make_headers(
        "post",
        url,
        request_id,
        json_body,
        psu_ip_address=requester_ip,
    )
    r = requests.post(url, data=json_body, headers=headers, cert=TLS_CERTS)
    r.raise_for_status()
    parsed_json = r.json()
    oauth_url = "".join(
        [
            OAUTH_URL_PREFIX,
            "client_id=" + CLIENT_ID + "&",
            "state={}&",
            "scope=" + "AIS:" + parsed_json["consentId"] + "&",
            "code_challenge=12345&",
            "code_challenge_method=Plain&",
            "redirect_uri=" + redirect_url,
        ]
    )
    return parsed_json["consentId"], oauth_url


def retrieve_access_token(access_code: str, redirect_url: str, requester_ip: str = ""):
    body = {
        "client_id": CLIENT_ID,
        "grant_type": "authorization_code",
        "code": access_code,
        "code_verifier": "12345",  # Not needed.
        "state": "state12345",  #  Not needed.
        "redirect_uri": redirect_url,
    }
    url_body = urlencode(body, doseq=False)
    request_id = str(uuid.uuid4())
    headers = make_headers(
        "post",
        ACCESS_TOKEN_URL,
        request_id,
        url_body,
        content_type="application/x-www-form-urlencoded;charset=UTF-8",
        psu_ip_address=requester_ip,
    )
    r = requests.post(ACCESS_TOKEN_URL, data=url_body, headers=headers, cert=TLS_CERTS)
    r.raise_for_status()
    return r.json()


def delete_consent(consent_id, access_token):
    url = f"{API_URL_PREFIX}consents/{consent_id}"
    request_id = str(uuid.uuid4())
    headers = make_headers(
        "get",
        url,
        request_id,
        "",
        extra_headers={"Authorization": f"Bearer {access_token}"},
    )
    r = requests.delete(url, data="", headers=headers, cert=TLS_CERTS)
    r.raise_for_status()
    return r.json()


def read_transaction_list(
    consent_id, access_token, account_id, date_from, requester_ip: str = ""
):
    booking_status = "booked"  # booked, pending or both
    with_balance = "true"
    url = (
        f"{API_URL_PREFIX}accounts/{account_id}/"
        f"transactions?bookingStatus={booking_status}&dateFrom={date_from}&"
        f"withBalance={with_balance}&download=true"
    )
    request_id = str(uuid.uuid4())
    headers = make_headers(
        "get",
        url,
        request_id,
        "",
        extra_headers={
            "Authorization": f"Bearer {access_token}",
            "Consent-ID": consent_id,
        },
        psu_ip_address=requester_ip,
    )
    r = requests.get(url, data="", headers=headers, cert=TLS_CERTS)
    r.raise_for_status()
    return r.content


def read_account_information(consent_id, access_token, requester_ip: str = ""):
    url = f"{API_URL_PREFIX}accounts"
    request_id = str(uuid.uuid4())
    headers = make_headers(
        "get",
        url,
        request_id,
        "",
        extra_headers={
            "Authorization": f"Bearer {access_token}",
            "Consent-ID": consent_id,
        },
        psu_ip_address=requester_ip,
    )
    r = requests.get(url, data="", headers=headers, cert=TLS_CERTS)
    r.raise_for_status()
    return r.json()
