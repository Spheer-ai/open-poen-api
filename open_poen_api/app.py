from fastapi import FastAPI, Depends
from .utils.load_env import load_env_vars
from .user_manager import fastapi_users, auth_backend
from .database import create_db_and_tables
from .routes import router

load_env_vars()

app = FastAPI()

app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"]
)

app.include_router(router)


@app.on_event("startup")
async def on_startup():
    # TODO: Don't recreate db every time.
    await create_db_and_tables()
