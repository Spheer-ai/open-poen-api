from open_poen_api.database import (
    async_session_maker,
    engine,
)
from open_poen_api.app import app
from open_poen_api.schemas_and_models.models.entities import Base, User, Initiative
from open_poen_api.routes import superuser_dep, required_login_dep, optional_login_dep
from open_poen_api import user_manager as um
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import pytest_asyncio
import base64
import urllib.parse


async def retrieve_token_from_last_sent_email():
    """Gets the last send email from Mailhog, assumes it's an email reply to a password
    reset request and parses the token inside it to return it."""
    async with AsyncClient() as client:
        response = await client.get("http://localhost:8025/api/v2/messages")
        if response.status_code == 200:
            emails = response.json()["items"]
            if len(emails) > 0:
                response = await client.get(
                    f"http://localhost:8025/api/v1/messages/{emails[0]['ID']}"
                )
                text = base64.b64decode(
                    response.json()["MIME"]["Parts"][0]["Body"]
                ).decode("utf-8")
                lines = text.split("\n")
                try:
                    url = next(line for line in lines if "reset-password" in line)
                except StopIteration:
                    raise ValueError("No reset-password found.")
                path = urllib.parse.urlparse(url).path
                _, token = path.split("/reset-password/")
                return token
            else:
                raise ValueError("No emails present.")
        else:
            raise ValueError("Request to Mailhog failed.")


@pytest_asyncio.fixture
async def get_mock_user(request):
    user_info = request.param
    if user_info["return_none"]:
        val = None
    else:
        val = User(
            id=user_info["obj_id"],
            role=user_info["role"],
            email=user_info["email"],
            is_active=user_info["is_active"],
            is_superuser=user_info["is_superuser"],
            is_verified=user_info["is_verified"],
        )

    async def func():
        return val

    return func


@pytest_asyncio.fixture
async def overridden_app(get_mock_user):
    app.dependency_overrides[superuser_dep] = get_mock_user
    app.dependency_overrides[required_login_dep] = get_mock_user
    app.dependency_overrides[optional_login_dep] = get_mock_user
    yield app
    app.dependency_overrides = {}


@pytest_asyncio.fixture
async def async_client(event_loop, overridden_app):
    async with AsyncClient(
        app=overridden_app, base_url="http://localhost:8000"
    ) as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def async_session(event_loop) -> AsyncSession:
    async with async_session_maker() as s:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        yield s

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def user_created_by_admin(async_client, async_session):
    # We intentionally don't add them with the session, because this
    # routes sets a temporary password and sends an email with instructions
    # as well.
    test_user = {"email": "existing@user.com"}
    response = await async_client.post("/user", json=test_user)
    return test_user


# @pytest_asyncio.fixture(scope="function")
# async def async_session_init(async_session):
#     user1 = User(
#         email="superuser@example.com",
#         role="user",
#         hashed_password="",
#         is_superuser=True,
#         is_verified=True,
#     )
#     user2 = User(
#         email="normaluser@example.com",
#         role="user",
#         hashed_password="",
#         is_superuser=False,
#         is_verified=True,
#     )
#     async_session.add_all([user1, user2])
#     await async_session.commit()
#     initiative1 = Initiative(
#         name="Initiative 1",
#         description="Description 1",
#         target_audience="Target Audience 1",
#         owner="Owner 1",
#         owner_email="email1@example.com",
#         address_applicant="Address 1",
#         kvk_registration="Registration 1",
#         location="Location 1",
#         hidden_sponsors=False,
#         initiative_owners=[user2],
#     )
#     async_session.add_all([initiative1])
#     await async_session.commit()
#     yield async_session
#     return


# @pytest.fixture(scope="function")
# def session_2(clean_session, pwd_context):
#     # We add some entities to the database that don't require a
#     # relationship upon instantiation.
#     hashed_debug_password = pwd_context.hash(temp_password_generator())
#     user1 = User(
#         email="user1@example.com",
#         role="admin",
#         hashed_password=hashed_debug_password,
#     )
#     user2 = User(
#         email="user2@example.com",
#         first_name="Mark",
#         last_name="de Wijk",
#         role="financial",
#         hashed_password=hashed_debug_password,
#     )
#     user3 = User(
#         email="user3@example.com",
#         hashed_password=hashed_debug_password,
#     )
#     clean_session.add_all([user1, user2, user3])
#     clean_session.commit()
#     clean_session.refresh(user2)
#     clean_session.refresh(user3)

#     initiative1 = Initiative(
#         name="Initiative 1",
#         description="Description 1",
#         purpose="Purpose 1",
#         target_audience="Target Audience 1",
#         owner="Owner 1",
#         owner_email="email1@example.com",
#         address_applicant="Address 1",
#         kvk_registration="Registration 1",
#         location="Location 1",
#         hidden=True,
#         initiative_owners=[user3, user2],
#     )

#     initiative2 = Initiative(
#         name="Initiative 2",
#         description="Description 2",
#         purpose="Purpose 2",
#         target_audience="Target Audience 2",
#         owner="Owner 2",
#         owner_email="email2@example.com",
#         address_applicant="Address 2",
#         kvk_registration="Registration 2",
#         location="Location 2",
#     )
#     clean_session.add_all([initiative1, initiative2])
#     clean_session.commit()

#     yield clean_session
#     return


# @pytest.fixture(scope="function")
# def session_3(session_2, pwd_context):
#     hashed_debug_password = pwd_context.hash(temp_password_generator())
#     user4 = User(
#         email="user4@example.com",
#         hashed_password=hashed_debug_password,
#     )
#     activity1 = Activity(
#         name="Activity 1",
#         description="Description 1",
#         purpose="Purpose 1",
#         target_audience="Target Audience 1",
#         initiative_id=1,
#         activity_owners=[user4],
#     )
#     activity2 = Activity(
#         name="Activity 2",
#         description="Description 2",
#         purpose="Purpose 2",
#         target_audience="Target Audience 2",
#         initiative_id=2,
#     )
#     payment1 = Payment(
#         booking_date=datetime.now().isoformat(),
#         transaction_amount=-33.33,
#         creditor_name="Some Name",
#         creditor_account="NL3400992211",
#         debtor_name="Another Name",
#         debtor_account="DE94772012",
#         short_user_description="Test short description",
#         long_user_description="Test long description",
#         route="expenses",
#         initiative_id=1,
#     )
#     payment2 = Payment(
#         booking_date=datetime.now().isoformat(),
#         transaction_amount=-33.33,
#         creditor_name="Some Name",
#         creditor_account="NL3400992211",
#         debtor_name="Another Name",
#         debtor_account="DE94772012",
#         short_user_description="Test short description",
#         long_user_description="Test long description",
#         route="expenses",
#         initiative_id=2,
#     )
#     session_2.add_all([activity1, activity2, payment1, payment2])
#     session_2.commit()

#     yield session_2


# def generate_auth_header(username: str, client, session):
#     data = {"username": username, "password": "DEBUG_PASSWORD"}
#     headers = {"Content-Type": "application/x-www-form-urlencoded"}

#     response = client.post("/token", headers=headers, data=data)
#     assert response.status_code == 200
#     assert (
#         "access_token" in response.json() and response.json()["token_type"] == "bearer"
#     )
#     return {"Authorization": f"Bearer {response.json()['access_token']}"}


# UserID = int
# InitiativeID = int
# ActivityID = int
# AuthTestUserConfig = tuple[dict[str, str], UserID]
# AuthTestInitiativeConfig = tuple[dict[str, str], InitiativeID, ActivityID]


# # TESTING USER PERMISSIONS
# @pytest.fixture(scope="function")
# def user_admin_2(client, session_2) -> AuthTestUserConfig:
#     # Admin edits/queries another user.
#     email = "user1@example.com"
#     return generate_auth_header(email, client, session_2), 2


# @pytest.fixture(scope="function")
# def user_financial_2(client, session_2) -> AuthTestUserConfig:
#     # Financial edits/queries another user.
#     email = "user2@example.com"
#     return generate_auth_header(email, client, session_2), 1


# @pytest.fixture(scope="function")
# def user_user_owner_2(client, session_2) -> AuthTestUserConfig:
#     # User Owner edits/queries himself.
#     email = "user3@example.com"
#     return generate_auth_header(email, client, session_2), 3


# @pytest.fixture(scope="function")
# def user_user_2(client, session_2) -> AuthTestUserConfig:
#     # A user edits/queries another user.
#     email = "user3@example.com"
#     return generate_auth_header(email, client, session_2), 1


# @pytest.fixture(scope="function")
# def user_guest_2(client, session_2) -> AuthTestUserConfig:
#     # A guest edits/queries a user.
#     return {}, 1


# # TESTING INITIATIVE PERMISSIONS
# @pytest.fixture(scope="function")
# def init_admin_3(client, session_3) -> AuthTestInitiativeConfig:
#     # Admin edits/queries an initiative/activity without being initiative owner
#     email = "user1@example.com"
#     return generate_auth_header(email, client, session_3), 1, 1


# @pytest.fixture(scope="function")
# def init_financial_3(client, session_3) -> AuthTestInitiativeConfig:
#     # Financial edits/queries an initiative/activity that he is linked to
#     email = "user2@example.com"
#     return generate_auth_header(email, client, session_3), 1, 1


# @pytest.fixture(scope="function")
# def init_initiative_owner_3(client, session_3) -> AuthTestInitiativeConfig:
#     # Initiative Owner edits/queries an initiative/activity the he is linked to.
#     email = "user3@example.com"
#     return generate_auth_header(email, client, session_3), 1, 1


# @pytest.fixture(scope="function")
# def init_activity_owner_3(client, session_3) -> AuthTestInitiativeConfig:
#     # Activity Owner edits/queries an initiative/activity that he is linked to.
#     email = "user4@example.com"
#     return generate_auth_header(email, client, session_3), 1, 1


# @pytest.fixture(scope="function")
# def init_user_3(client, session_3) -> AuthTestInitiativeConfig:
#     # A user that edits/queries an initiative/activity for which he has no rights.
#     email = "user3@example.com"
#     return generate_auth_header(email, client, session_3), 2, 1


# @pytest.fixture(scope="function")
# def init_guest_3(client, session_3) -> AuthTestInitiativeConfig:
#     # A guest edits/queries an initiative/activity.
#     return {}, 1, 1


# @pytest.fixture
# def initiative_data():
#     return {
#         "name": "Piets Buurtbarbeque",
#         "description": "Piet wordt vijftig.",
#         "purpose": "Saamhorigheid in de buurt bevorderen.",
#         "target_audience": "Mensen uit buurt De Florijn.",
#         "owner": "Mark de Wijk",
#         "owner_email": "markdewijk@spheer.ai",
#         "address_applicant": "Het stoepje 42, Assen, 9408DT, Nederland",
#         "kvk_registration": "12345678",
#         "location": "Amsterdam",
#     }


# @pytest.fixture
# def activity_data():
#     return {
#         "name": "Vlees- en Drinkwaren",
#         "description": "Eten voor de barbeque",
#         "purpose": "Ervoor zorgen dat er voldoende te eten en te drinken is",
#         "target_audience": "Alle bezoekers",
#     }


# @pytest.fixture
# def payment_data():
#     return {
#         "booking_date": datetime.now().isoformat(),
#         "transaction_amount": 123.12,
#         "creditor_name": "Creditor Test",
#         "creditor_account": "CR123456789",
#         "debtor_name": "Debtor Test",
#         "debtor_account": "DB123456789",
#         "short_user_description": "Test short description",
#         "long_user_description": "Test long description",
#         "route": "income",
#     }
