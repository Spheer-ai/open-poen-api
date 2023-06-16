import pytest
from open_poen_api.database import engine
from sqlmodel import Session, SQLModel
from fastapi.testclient import TestClient
from open_poen_api.app import app
from open_poen_api.models import User, Initiative, Activity
from open_poen_api.utils import temp_password_generator
from passlib.context import CryptContext
import pytest


@pytest.fixture(scope="function")
def clean_session():
    # Set up: Connect to test database and create session
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    yield session  # this is where the testing happens

    # Tear down: Close session and drop all data from test database
    session.close_all()
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def pwd_context():
    return CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.fixture(scope="function")
def session_2(clean_session, pwd_context):
    # We add some entities to the database that don't require a
    # relationship upon instantiation.
    hashed_debug_password = pwd_context.hash(temp_password_generator())
    user1 = User(
        email="user1@example.com",
        role="admin",
        hashed_password=hashed_debug_password,
    )
    user2 = User(
        email="user2@example.com",
        first_name="Mark",
        last_name="de Wijk",
        role="financial",
        hashed_password=hashed_debug_password,
    )
    user3 = User(
        email="user3@example.com",
        hidden=True,
        hashed_password=hashed_debug_password,
    )
    clean_session.add_all([user1, user2, user3])
    clean_session.commit()

    initiative1 = Initiative(
        name="Initiative 1",
        description="Description 1",
        purpose="Purpose 1",
        target_audience="Target Audience 1",
        owner="Owner 1",
        owner_email="email1@example.com",
        address_applicant="Address 1",
        kvk_registration="Registration 1",
        location="Location 1",
        hidden=True,
    )

    initiative2 = Initiative(
        name="Initiative 2",
        description="Description 2",
        purpose="Purpose 2",
        target_audience="Target Audience 2",
        owner="Owner 2",
        owner_email="email2@example.com",
        address_applicant="Address 2",
        kvk_registration="Registration 2",
        location="Location 2",
    )
    clean_session.add_all([initiative1, initiative2])
    clean_session.commit()

    yield clean_session
    return


@pytest.fixture(scope="function")
def session_3(session_2):
    activity1 = Activity(
        name="Activity 1",
        description="Description 1",
        purpose="Purpose 1",
        target_audience="Target Audience 1",
        initiative_id=1,
    )
    activity2 = Activity(
        name="Activity 2",
        description="Description 2",
        purpose="Purpose 2",
        target_audience="Target Audience 2",
        initiative_id=1,
    )
    session_2.add_all([activity1, activity2])
    session_2.commit()

    yield session_2


def generate_auth_header(username: str, client, session_2):
    data = {"username": username, "password": "DEBUG_PASSWORD"}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = client.post("/token", headers=headers, data=data)
    assert response.status_code == 200
    assert (
        "access_token" in response.json() and response.json()["token_type"] == "bearer"
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="function")
def admin_authorization_header(client, session_2):
    return generate_auth_header("user1@example.com", client, session_2)


@pytest.fixture(scope="function")
def financial_authorization_header(client, session_2):
    return generate_auth_header("user2@example.com", client, session_2)


@pytest.fixture(scope="function")
def user_authorization_header(client, session_2):
    return generate_auth_header("user3@example.com", client, session_2)
