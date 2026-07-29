"""Ensure every ORM table can compile for the production MySQL dialect."""

from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from app.core.database import Base


def test_all_tables_compile_for_mysql() -> None:
    """Catch backend-specific column and constraint mistakes without a live DB."""

    dialect = mysql.dialect()
    compiled = {
        table.name: str(CreateTable(table).compile(dialect=dialect))
        for table in Base.metadata.sorted_tables
    }
    assert len(compiled) >= 17
    assert "CREATE TABLE users" in compiled["users"]
    assert "LONGTEXT" in compiled["policies"]
    assert "user_document_checks" in compiled
