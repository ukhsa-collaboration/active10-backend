from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import DateTime

import models  # noqa: F401
from db.session import Base

GENERATORS = [
    pytest.param(getattr(column, kind), id=f"{table.name}.{column.name}.{kind}")
    for table in Base.metadata.sorted_tables
    for column in table.columns
    if isinstance(column.type, DateTime)
    for kind in ("default", "onupdate")
    if getattr(column, kind) is not None
]


def test_datetime_columns_with_generated_values_are_found():
    assert GENERATORS


@pytest.mark.parametrize("generator", GENERATORS)
def test_datetime_column_values_are_generated_per_row(generator):
    # A plain value here is evaluated once at import, so every row would share it.
    assert generator.is_callable

    assert abs(datetime.now(UTC) - generator.arg(None)) < timedelta(seconds=5)
