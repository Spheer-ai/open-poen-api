from .utils.load_env import DEBUG
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from .managers.user_manager import fastapi_users, auth_backend
from .managers import CustomException
from .database import create_db_and_tables, get_async_session
from .routes import user_router, initiative_router, funder_router, payment_router
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.cors import CORSMiddleware
import os

app = FastAPI()

app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"]
)

app.include_router(user_router)
app.include_router(funder_router)
app.include_router(initiative_router)
app.include_router(payment_router)


@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    return JSONResponse(status_code=exc.status_code, content=str(exc))


@app.on_event("startup")
async def on_startup():
    # TODO: Don't recreate db every time.
    await create_db_and_tables()
    pass


if not DEBUG:
    domain: str = os.environ["DOMAIN_NAME"]
    allowed_hosts = [domain, f"www.{domain}"]
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[f"https://{domain}", "localhost", "127.0.0.1"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
