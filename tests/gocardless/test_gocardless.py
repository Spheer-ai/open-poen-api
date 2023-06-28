from open_poen_api.gocardless import api as gcl
import pytest


@pytest.fixture(scope="module")
def token() -> gcl.Token:
    return gcl.create_new_token()


@pytest.fixture(scope="module")
def institutions(token) -> list[gcl.Institution]:
    return gcl.get_institutions(access_token=token.access)


def test_create_new_token():
    token = gcl.create_new_token()


def test_get_institutions(token):
    gcl.get_institutions(access_token=token.access)


def test_create_new_agreement(token, institutions):
    ing = [i for i in institutions if i.name == "ING"][0]
    gcl.create_new_agreement(access_token=token.access, institution=ing)
