from fastapi import FastAPI
from open_poen_api.routes import router

app = FastAPI()

app.include_router(router)
