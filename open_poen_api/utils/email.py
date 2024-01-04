from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi_mail.errors import PydanticClassRequired
from pydantic import BaseModel, EmailStr
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import os


class OpenPoenFastMail(FastMail):
    async def safe_send_message(self, message: MessageSchema) -> None:
        # Send email only to these persons if this runs in the acceptance environment
        # to prevent sending test emails to real users.
        if os.environ["ENVIRONMENT"] == "acceptance":
            emails = [EmailStr(i) for i in os.environ["EMAIL_RECIPIENTS"].split(",")]
            message.recipients = emails
        await super().send_message(message)

    async def send_message(
        self, message: MessageSchema, template_name: str | None = None
    ) -> None:
        raise NotImplementedError("Use safe_send_message instead")


def str_to_bool(env: str) -> bool:
    if env == "0":
        return False
    elif env == "1":
        return True
    else:
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
