from fastapi import FastAPI
from .routes import router
import uvicorn
from .utils.load_env import load_env

load_env()

app = FastAPI()
app.include_router(router)
