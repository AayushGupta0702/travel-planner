from sqlmodel import SQLModel, create_engine, Session
from app.config import DATABASE_URL

# check_same_thread=False is needed for SQLite to run in multi-threaded FastAPI.
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
        
def get_db_session():
    return Session(engine)
