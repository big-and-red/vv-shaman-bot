"""fill_tables

Revision ID: 249aedd25b30
Revises: 6d2550b56dab
Create Date: 2024-12-10 05:44:10.685965

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import insert, text

from data_interpretations.numbers_interpretations import numbers_interpretations
from data_interpretations.time_interpretations import time_interpretations
from db_helpers.models import NumberChoice, TimeChoice, TimeRange

# revision identifiers, used by Alembic.
revision: str = '249aedd25b30'
down_revision: Union[str, None] = '6d2550b56dab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    for time_key, time_data in time_interpretations.items():
        time_range = time_data["time_range"]

        op.execute(insert(TimeRange).values(name=time_key, time_range=time_range))

        time_range_id = op.get_bind().execute(
            text("SELECT id FROM time_ranges WHERE name = :name"),
            {"name": time_key}  # Используйте текущий time_key для получения id
        ).scalar()

        for choice_time, interpretation in time_data["interpretations"].items():
            op.execute(insert(TimeChoice).values(
                choice=choice_time,
                interpretation=interpretation,
                time_range_id=time_range_id
            ))

            # Наполнение таблицы NumberChoice, используя объект модели NumberChoice
    for number, interpretation in numbers_interpretations.items():
        op.execute(
            insert(NumberChoice).values(
                number=number,
                interpretation=interpretation
            )
        )


def downgrade():
    op.execute("DELETE FROM time_choices")
    op.execute("DELETE FROM time_ranges")
    op.execute("DELETE FROM numbers_choices")
