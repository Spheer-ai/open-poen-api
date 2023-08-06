import os
from dotenv import load_dotenv

load_dotenv()
DEBUG = os.getenv("ENVIRONMENT") == "debug"
if DEBUG:
    load_dotenv("debug.env", override=True)
elif os.getenv("ENVIRONMENT") == "production":
    load_dotenv("production.env", override=True)
