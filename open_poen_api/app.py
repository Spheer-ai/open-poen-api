from fastapi import FastAPI, Depends

# from .routes import router
import uvicorn
from .utils.load_env import load_env_vars
from .authorization import fastapi_users, auth_backend, current_active_user
from .schemas_and_models.models.entities import User
from .schemas_and_models import UserRead, UserUpdate
from .database import create_db_and_tables


load_env_vars()

app = FastAPI()

app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"]
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# app.include_router(router)


@app.get("/authenticated_route")
async def authenticated_route(user: User = Depends(current_active_user)):
    return {"message": f"Hello {user.email}"}


@app.on_event("startup")
async def on_startup():
    # TODO: Don't recreate db every time.
    await create_db_and_tables()
