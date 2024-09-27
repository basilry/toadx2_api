import os

from logging.config import fileConfig

from sqlalchemy import create_engine
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from src.config.database import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

database_url = 'postgresql://postgres:1234@localhost:5432/toadx2'

config.set_main_option('sqlalchemy.url', database_url)

# SQLAlchemy 엔진 생성
try:
    connectable = create_engine(database_url, poolclass=pool.NullPool)
    print("Engine created successfully.")
except Exception as e:
    print(f"Error creating engine: {e}")


# Online/Offline 모드에서 마이그레이션 실행
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
