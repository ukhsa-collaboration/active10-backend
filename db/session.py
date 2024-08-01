from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from utils.base_config import config

DATABASE_URL = f"mysql+mysqldb://{config.db_user}:{config.db_pass}@{config.db_host}:{config.db_port}/{config.db_name}"

Engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=Engine)

Base = declarative_base()


def get_db_session() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
