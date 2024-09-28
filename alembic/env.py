from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context
from src.database.database import Base
import os
from dotenv import load_dotenv
from src.database.models import kb_real_estate_data_hub

# .env 파일 로드
load_dotenv()

# Alembic 설정
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLAlchemy MetaData 설정
target_metadata = Base.metadata

# 데이터베이스 URL 가져오기
database_url = os.getenv("DATABASE_URL")

# Alembic에 DATABASE_URL 전달
config.set_main_option('sqlalchemy.url', database_url)

# SQLAlchemy 엔진 생성
connectable = create_engine(database_url, poolclass=pool.NullPool)


def run_migrations_online() -> None:
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,  # 스키마 차이를 정확히 비교
            compare_type=True,  # 컬럼 타입 변경 감지
            compare_server_default=True,  # 기본값 변경 감지
            compare_index=True  # 인덱스 변경 감지
        )

        with context.begin_transaction():
            context.run_migrations()


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True
    )

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
