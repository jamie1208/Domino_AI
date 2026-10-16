from sqlalchemy.orm import Session

from app.db_models import DataChangeLogRecord


class Repository:
    def __init__(self, session: Session):
        self.session = session

    def log_change(self, table: str, key: str, change_type: str, version: int, after: dict, before: dict | None = None) -> None:
        self.session.add(DataChangeLogRecord(table_name=table, record_key=key, change_type=change_type, version=version, before_snapshot=before, after_snapshot=after))
