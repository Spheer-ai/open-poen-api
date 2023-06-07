from . import models
from sqlmodel import create_engine, SQLModel, Session

# TODO: Configure this with environment variables.
DATABASE_URL = "postgresql://mark:mark@localhost:5432/open-poen-dev"
engine = create_engine(DATABASE_URL)
SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
