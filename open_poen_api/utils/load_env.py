import os
from dotenv import load_dotenv


def load_env():
    load_dotenv()
    if os.getenv("ENVIRONMENT") == "debug":
        load_dotenv(".env.debug")
    elif os.getenv("ENVIRONMENT") == "production":
        load_dotenv(".env.production")
