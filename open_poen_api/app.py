from fastapi import FastAPI
from .routes import router
import uvicorn
from .utils.load_env import load_env_vars

load_env_vars()

app = FastAPI()
app.include_router(router)
