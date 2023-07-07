from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import BaseModel, EmailStr
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import os


TEMPLATE_FOLDER = Path(__file__).parent.parent / "templates"


def env_var(var_name):
    return os.environ.get(var_name)


env = Environment(loader=FileSystemLoader(TEMPLATE_FOLDER))
env.globals["env_var"] = env_var


class EmailSchema(BaseModel):
    email: list[EmailStr]


conf = ConnectionConfig(
    MAIL_USERNAME="",
    MAIL_PASSWORD="",
    MAIL_FROM=EmailStr("test@email.com"),
    MAIL_PORT=1025,
    MAIL_SERVER="localhost",
    MAIL_FROM_NAME="Desired Name",
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=False,
    VALIDATE_CERTS=False,
    TEMPLATE_FOLDER=TEMPLATE_FOLDER,
)
