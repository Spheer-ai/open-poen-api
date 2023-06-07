from fastapi import FastAPI
from .routes import router
import uvicorn

app = FastAPI()
app.include_router(router)
