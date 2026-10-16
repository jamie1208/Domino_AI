"""Regression for fresh PostgreSQL Alembic chain and dynamic 0001 metadata.

Requires TEST_DATABASE_URL to be a disposable PostgreSQL test database whose
role is permitted to CREATE SCHEMA. Never use DATABASE_URL/production here.
"""
import os
import subprocess
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="isolated PostgreSQL test database required")
def test_fresh_postgres_schema_0001_to_0005_and_repeat_upgrade():
    raw_url = os.environ["TEST_DATABASE_URL"]
    parsed = make_url(raw_url)
    if not parsed.drivername.startswith("postgresql"):
        pytest.skip("This integration requires a PostgreSQL test database")

    schema = "domino_fresh_" + uuid4().hex[:12]
    admin_engine = create_engine(parsed)
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    # psycopg/libpq options forces every Alembic and SQLAlchemy connection to
    # resolve its unqualified table names in this new isolated schema.
    isolated_url = parsed.update_query_dict({"options": f"-csearch_path={schema}"})
    test_engine = create_engine(isolated_url)
    try:
        with test_engine.connect() as connection:
            assert inspect(connection).get_table_names() == []

        env = {**os.environ, "DATABASE_URL": isolated_url.render_as_string(hide_password=False)}
        for _ in range(2):
            subprocess.run(
                [".venv/bin/alembic", "upgrade", "head"],
                env=env, check=True, capture_output=True, text=True,
            )

        with test_engine.connect() as connection:
            inspector = inspect(connection)
            names = set(inspector.get_table_names())
            assert {"companies", "evidence", "source_ingestion_runs", "public_documents", "public_document_chunks", "alembic_version"} <= names
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261016_0005"
            assert {"source_metadata", "source_published_at"} <= {
                col["name"] for col in inspector.get_columns("public_documents")
            }
            assert "ix_public_documents_key_time" in {
                item["name"] for item in inspector.get_indexes("public_documents")
            }
            assert "ix_document_chunks_document" in {
                item["name"] for item in inspector.get_indexes("public_document_chunks")
            }
            assert "ix_source_runs_key_retrieved" in {
                item["name"] for item in inspector.get_indexes("source_ingestion_runs")
            }
    finally:
        test_engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin_engine.dispose()
