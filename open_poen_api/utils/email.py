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


print(os.environ["MAIL_SERVER"])

conf = ConnectionConfig(
    MAIL_USERNAME=os.environ["MAIL_USERNAME"],
    MAIL_PASSWORD=os.environ["MAIL_PASSWORD"],
    MAIL_FROM=EmailStr(os.environ["MAIL_FROM"]),
    MAIL_PORT=int(os.environ["MAIL_PORT"]),
    MAIL_SERVER=os.environ["MAIL_SERVER"],
    MAIL_FROM_NAME=os.environ["MAIL_FROM_NAME"],
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=False,
    VALIDATE_CERTS=False,
    TEMPLATE_FOLDER=TEMPLATE_FOLDER,
)
