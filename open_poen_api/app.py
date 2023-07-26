from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from .utils.load_env import load_env_vars
from .managers.user_manager import fastapi_users, auth_backend
from .managers import CustomException
from .database import create_db_and_tables, get_async_session
from .routes import router
from sqlalchemy.ext.asyncio import AsyncSession

load_env_vars()

app = FastAPI()

app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"]
)

app.include_router(router)


@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    return JSONResponse(status_code=exc.status_code, content=str(exc))


@app.on_event("startup")
async def on_startup():
    # TODO: Don't recreate db every time.
    await create_db_and_tables()
