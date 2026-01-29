from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.config import DB_URL

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)
