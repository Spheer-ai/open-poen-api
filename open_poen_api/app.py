from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .managers.user_manager import fastapi_users, auth_backend
from .managers import CustomException
from .database import create_db_and_tables
from .routes import (
    user_router,
    initiative_router,
    funder_router,
    payment_router,
    permission_router,
    utils_router,
)
from starlette.middleware.cors import CORSMiddleware
import os
from .logger import audit_logger


tags_metadata = [
    {"name": "auth"},
    {"name": "user"},
    {
        "name": "funder",
        "description": "A **funder** is any entity that is willing to finance an **initiative**. It does this by issuing a **grant** under a **regulation**. For this grant, one or multiple initiatives can be made.",
    },
    {
        "name": "initiative",
        "description": "An **initiative** is an intention to spend a **funder**'s money in a certain way. It can be subdivided into **activities**. **Payments** can be added to an initiative by a **user** if a **bank account** is coupled, if a **debit card** is assigned to the initiative by a super user or administrator, or if a super user or administrator creates a payment manually. When the initiative is finished, it's finances will be verified.",
    },
    {
        "name": "payment",
        "description": "A **payment** can be of three types: **manual**, **GoCardless** or **BNG**. Manual means that it was created manually, GoCardless that it was imported through a coupled **bank account** and BNG that it was imported from the BNG account through a **Debit Card**.",
    },
]


app = FastAPI(
    title="Open Poen API",
    description="Creating transparency in how public funds are spent.",
    openapi_tags=tags_metadata,
)

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
app.include_router(permission_router, prefix="/auth/entity-access", tags=["auth"])
app.include_router(utils_router)


@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    audit_logger.info(
        f"Custom Exception occurred with status code {exc.status_code} and message:\n{exc.message}"
    )
    return JSONResponse(status_code=exc.status_code, content=exc.message)


@app.exception_handler(Exception)
async def all_exception_handler(request: Request, exc: Exception):
    audit_logger.error(f"Unexpected exception occurred with stack trace:\n{str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An error occurred on the server."},
    )


if os.environ["ENVIRONMENT"] == "debug":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )

    # @app.on_event("startup")
    # async def on_startup():
    #     # TODO: Don't recreate db every time.
    #     await create_db_and_tables()
    #     pass
