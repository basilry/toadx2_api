import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

database_host = os.getenv('DATABASE_HOST')
database_port = os.getenv('DATABASE_PORT')
database_name = os.getenv('DATABASE_NAME')
postgres_user = os.getenv('POSTGRESQL_USER')
postgres_password = os.getenv('POSTGRESQL_PASSWORD')

DATABASE_URL = f'postgresql://{postgres_user}:{postgres_password}@{database_host}:{database_port}/{database_name}'

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
