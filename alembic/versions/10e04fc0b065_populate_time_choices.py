"""populate time_choices

Revision ID: 10e04fc0b065
Revises: 4dff3b4a5446
Create Date: 2024-10-01 00:39:42.757037

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import insert
from sqlalchemy import text

from db_helpers.models import TimeChoice, TimeRange
from time_data.time_interpretations import time_interpretations

# revision identifiers, used by Alembic.
revision: str = '10e04fc0b065'
down_revision: Union[str, None] = '4dff3b4a5446'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Проходите по словарю и добавляйте данные в таблицу
    for time_key, time_data in time_interpretations.items():
        time_range = time_data["time_range"]

        # Вставляем новый временной диапазон, если он еще не существует
        op.execute(insert(TimeRange).values(name=time_key, time_range=time_range))

        # Получаем ID добавленного временного диапазона
        time_range_id = op.get_bind().execute(
            text("SELECT id FROM time_ranges WHERE name = :name"),
            {"name": time_key}  # Используйте текущий time_key для получения id
        ).scalar()

        # Проходим по интерпретациям и вставляем их в таблицу time_choices
        for choice_time, interpretation in time_data["interpretations"].items():
            op.execute(insert(TimeChoice).values(
                choice=choice_time,
                interpretation=interpretation,
                time_range_id=time_range_id
            ))


def downgrade():
    # Код для удаления данных (если необходимо)
    op.execute("DELETE FROM time_choices")
    op.execute("DELETE FROM time_ranges")
