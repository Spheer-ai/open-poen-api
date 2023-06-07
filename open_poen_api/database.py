import open_poen_api.models
from sqlmodel import create_engine, SQLModel, Session

DATABASE_URL = "postgresql://mark:mark@localhost:5432/open-poen-dev"
engine = create_engine(DATABASE_URL)
SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
