import pytest
from open_poen_api.database import engine
from sqlmodel import Session, SQLModel
from fastapi.testclient import TestClient
from open_poen_api.app import app
from open_poen_api.schemas_and_models.models.entities import User, Initiative, Activity
from open_poen_api.utils import temp_password_generator
from passlib.context import CryptContext
import pytest
from datetime import datetime


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
        hashed_password=hashed_debug_password,
    )
    clean_session.add_all([user1, user2, user3])
    clean_session.commit()
    clean_session.refresh(user3)

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
        initiative_owners=[user3, user2],
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


UserID = int | None
InitiativeID = int | None
ActivityID = int | None
AuthTestConfig = tuple[dict[str, str], UserID, InitiativeID, ActivityID]


@pytest.fixture(scope="function")
def admin_auth_2(client, session_2) -> AuthTestConfig:
    email = "user1@example.com"
    return generate_auth_header(email, client, session_2), 1, 1, None


@pytest.fixture(scope="function")
def financial_auth_2(client, session_2) -> AuthTestConfig:
    email = "user2@example.com"
    return generate_auth_header(email, client, session_2), 1, 1, None


@pytest.fixture(scope="function")
def initiative_owner_auth_2(client, session_2) -> AuthTestConfig:
    email = "user3@example.com"
    return generate_auth_header(email, client, session_2), 3, 1, None


@pytest.fixture(scope="function")
def user_auth_2(client, session_2) -> AuthTestConfig:
    email = "user3@example.com"
    return generate_auth_header(email, client, session_2), 1, 1, None


@pytest.fixture(scope="function")
def user_owner_auth_2(client, session_2) -> AuthTestConfig:
    email = "user3@example.com"
    return generate_auth_header(email, client, session_2), 3, None, None


@pytest.fixture(scope="function")
def guest_auth_2(client, session_2) -> AuthTestConfig:
    return {}, 1, 1, None


@pytest.fixture
def initiative_data():
    return {
        "name": "Piets Buurtbarbeque",
        "description": "Piet wordt vijftig.",
        "purpose": "Saamhorigheid in de buurt bevorderen.",
        "target_audience": "Mensen uit buurt De Florijn.",
        "owner": "Mark de Wijk",
        "owner_email": "markdewijk@spheer.ai",
        "address_applicant": "Het stoepje 42, Assen, 9408DT, Nederland",
        "kvk_registration": "12345678",
        "location": "Amsterdam",
    }


@pytest.fixture
def activity_data():
    return {
        "name": "Vlees- en Drinkwaren",
        "description": "Eten voor de barbeque",
        "purpose": "Ervoor zorgen dat er voldoende te eten en te drinken is",
        "target_audience": "Alle bezoekers",
    }


@pytest.fixture
def payment_data():
    return {
        "booking_date": datetime.now().isoformat(),
        "transaction_amount": 123.12,
        "creditor_name": "Creditor Test",
        "creditor_account": "CR123456789",
        "debtor_name": "Debtor Test",
        "debtor_account": "DB123456789",
        "short_user_description": "Test short description",
        "long_user_description": "Test long description",
        "route": "income",
    }
