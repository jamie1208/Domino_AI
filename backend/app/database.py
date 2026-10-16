"""Database configuration kept outside Skills and orchestration."""
import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


class DatabaseNotConfiguredError(RuntimeError):
    pass


def database_url() -> str:
    url = os.getenv('DATABASE_URL', '').strip()
    if not url:
        raise DatabaseNotConfiguredError('DATABASE_URL 未設定，分析持久化功能不可用。')
    return url


@lru_cache(maxsize=4)
def engine_for_url(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True)


def session_factory(url: str | None = None) -> sessionmaker[Session]:
    resolved = url or database_url()
    return sessionmaker(bind=engine_for_url(resolved), expire_on_commit=False)


def clear_engine_cache() -> None:
    engine_for_url.cache_clear()
