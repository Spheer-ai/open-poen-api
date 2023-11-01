import pytest
from tests.conftest import clean_async_client, async_session
from open_poen_api.cli import async_add_user


async def test_flow(clean_async_client, async_session):
    # Add user
    await async_add_user("mark@groningen.nl", True, "user", password="test")
    # Login
    response = await clean_async_client.post(
        "/auth/jwt/login",
        data={"username": "mark@groningen.nl", "password": "test"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    auth_header = {"Authorization": "Bearer " + response.json()["access_token"]}
    # List users
    response = await clean_async_client.get("/users", headers=auth_header)
    assert response.status_code == 200
    assert len(response.json()["users"]) == 1
    # Create funder
    response = await clean_async_client.post(
        "/funder",
        json={"name": "Gemeente Amsterdam", "url": "https://amsterdam.nl"},
        headers=auth_header,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Gemeente Amsterdam"
    # Create regulation
    response = await clean_async_client.post(
        "/funder/1/regulation",
        json={
            "name": "Buurtprojecten",
            "description": "Buurtprojecten in Amsterdam Oost",
        },
        headers=auth_header,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Buurtprojecten"
    # Create grant
    response = await clean_async_client.post(
        "/funder/1/regulation/1/grant",
        json={
            "name": "Boerenmarkt op Westerplein",
            "reference": "AO-1991",
            "budget": 1000,
        },
        headers=auth_header,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Boerenmarkt op Westerplein"
    # Create an overseer
    response = await clean_async_client.post(
        "/user",
        json={
            "email": "jamal@leiria.pt",
            "first_name": "Jamal",
            "last_name": "Vleij",
            "role": "user",
        },
        headers=auth_header,
    )
    assert response.status_code == 200
    jamal = response.json()
    assert jamal["email"] == "jamal@leiria.pt"
    response = await clean_async_client.patch(
        "/funder/1/regulation/1/grant/1/overseers",
        json={"user_ids": [jamal["id"]]},
        headers=auth_header,
    )
    assert len(response.json()["users"]) == 1
    # Create an officer
    response = await clean_async_client.post(
        "/user",
        json={
            "email": "jaapkoen@amsterdam.nl",
            "first_name": "Jaap Koen",
            "last_name": "Bijma",
            "role": "user",
        },
        headers=auth_header,
    )
    assert response.status_code == 200
    jaap_koen = response.json()
    assert jaap_koen["email"] == "jaapkoen@amsterdam.nl"
    response = await clean_async_client.patch(
        "/funder/1/regulation/1/officers",
        json={"user_ids": [jaap_koen["id"]], "role": "grant officer"},
        headers=auth_header,
    )
    assert len(response.json()["users"]) == 1
    # Get regulation detail view
    response = await clean_async_client.get(
        "/funder/1/regulation/1", headers=auth_header
    )
    assert response.json()["grant_officers"][0]["email"] == "jaapkoen@amsterdam.nl"
    assert response.json()["grants"][0]["name"] == "Boerenmarkt op Westerplein"
    assert response.json()["funder"]["name"] == "Gemeente Amsterdam"
    # Get grant detail view
    response = await clean_async_client.get(
        "/funder/1/regulation/1/grant/1", headers=auth_header
    )
    assert response.json()["regulation"]["name"] == "Buurtprojecten"
    assert response.json()["overseers"][0]["email"] == "jamal@leiria.pt"
    # Get funders list
    response = await clean_async_client.get("/funders")
    assert len(response.json()["funders"]) == 1
    # Get regulations list
    response = await clean_async_client.get("/funder/1/regulations")
    assert len(response.json()["regulations"]) == 1
    # Get grant list
    response = await clean_async_client.get("/funder/1/regulation/1/grants")
    assert len(response.json()["grants"]) == 1
