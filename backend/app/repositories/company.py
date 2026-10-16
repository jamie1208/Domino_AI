from datetime import datetime

from sqlalchemy import or_, select

from app.db_models import CompanyRecord
from app.repositories.base import Repository


class CompanyRepository(Repository):
    def create_version(self, *, company_key: str, name: str, valid_from: datetime, ticker: str | None = None, market: str | None = None, is_synthetic: bool = False, metadata: dict | None = None) -> CompanyRecord:
        latest = self.session.scalar(select(CompanyRecord).where(CompanyRecord.company_key == company_key).order_by(CompanyRecord.version.desc()).limit(1))
        version = 1 if latest is None else latest.version + 1
        before = None
        if latest and latest.valid_to is None:
            before = {'name': latest.name, 'valid_to': None}
            latest.valid_to = valid_from
        record = CompanyRecord(company_key=company_key, version=version, name=name, ticker=ticker, market=market, is_synthetic=is_synthetic, valid_from=valid_from, metadata_json=metadata or {})
        self.session.add(record)
        self.session.flush()
        self.log_change('companies', company_key, 'create' if version == 1 else 'supersede', version, {'id': record.id, 'name': name, 'valid_from': valid_from.isoformat()}, before)
        return record

    def get_at(self, company_key: str, as_of: datetime) -> CompanyRecord | None:
        return self.session.scalar(select(CompanyRecord).where(CompanyRecord.company_key == company_key, CompanyRecord.valid_from <= as_of, or_(CompanyRecord.valid_to.is_(None), CompanyRecord.valid_to > as_of)).order_by(CompanyRecord.version.desc()).limit(1))

    def history(self, company_key: str) -> list[CompanyRecord]:
        return list(self.session.scalars(select(CompanyRecord).where(CompanyRecord.company_key == company_key).order_by(CompanyRecord.version)))
