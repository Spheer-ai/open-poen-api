from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import BaseModel, EmailStr
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import os


def str_to_bool(env: str) -> bool:
    if env == "0":
        return False
    elif env == "1":
        return True
    else:
        print(type(env))
        print(env)
        raise ValueError("Ambiguous environment variable")


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
    MAIL_STARTTLS=str_to_bool(os.environ["MAIL_STARTTLS"]),
    MAIL_SSL_TLS=str_to_bool(os.environ["MAIL_SSL_TLS"]),
    USE_CREDENTIALS=str_to_bool(os.environ["USE_CREDENTIALS"]),
    VALIDATE_CERTS=str_to_bool(os.environ["VALIDATE_CERTS"]),
    TEMPLATE_FOLDER=TEMPLATE_FOLDER,
)
