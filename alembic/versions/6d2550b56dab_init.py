"""Init

Revision ID: 6d2550b56dab
Revises: 
Create Date: 2024-12-10 05:43:40.516343

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '6d2550b56dab'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Проверяет существование таблицы"""
    inspector = Inspector.from_engine(op.get_bind())
    return table_name in inspector.get_table_names()


def create_table_if_not_exists(table_name: str, create_table_func):
    """Создает таблицу, если она не существует"""
    if not table_exists(table_name):
        create_table_func()


def upgrade() -> None:
    # numbers_choices
    def create_numbers_choices():
        op.create_table('numbers_choices',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('number', sa.Integer(), nullable=True),
            sa.Column('interpretation', sa.String(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_numbers_choices_id'), 'numbers_choices', ['id'], unique=False)
        op.create_index(op.f('ix_numbers_choices_number'), 'numbers_choices', ['number'], unique=False)
    create_table_if_not_exists('numbers_choices', create_numbers_choices)

    # time_ranges
    def create_time_ranges():
        op.create_table('time_ranges',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(), nullable=True),
            sa.Column('time_range', sa.String(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_time_ranges_id'), 'time_ranges', ['id'], unique=False)
        op.create_index(op.f('ix_time_ranges_name'), 'time_ranges', ['name'], unique=True)
        op.create_index(op.f('ix_time_ranges_time_range'), 'time_ranges', ['time_range'], unique=False)
    create_table_if_not_exists('time_ranges', create_time_ranges)

    # users
    def create_users():
        op.create_table('users',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('username', sa.String(), nullable=True),
            sa.Column('tg_id', sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('tg_id')
        )
        op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
        op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    create_table_if_not_exists('users', create_users)

    # number_selections
    def create_number_selections():
        op.create_table('number_selections',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('number_choice_id', sa.Integer(), nullable=False),
            sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['number_choice_id'], ['numbers_choices.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_number_selections_id'), 'number_selections', ['id'], unique=False)
    create_table_if_not_exists('number_selections', create_number_selections)

    # time_choices
    def create_time_choices():
        op.create_table('time_choices',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('choice', sa.String(), nullable=True),
            sa.Column('interpretation', sa.String(), nullable=True),
            sa.Column('time_range_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['time_range_id'], ['time_ranges.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_time_choices_choice'), 'time_choices', ['choice'], unique=False)
        op.create_index(op.f('ix_time_choices_id'), 'time_choices', ['id'], unique=False)
    create_table_if_not_exists('time_choices', create_time_choices)

    # time_selections
    def create_time_selections():
        op.create_table('time_selections',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('time_choice_id', sa.Integer(), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['time_choice_id'], ['time_choices.id'], name='fk_time_selection_time_choice'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_time_selections_id'), 'time_selections', ['id'], unique=False)
    create_table_if_not_exists('time_selections', create_time_selections)


def downgrade() -> None:
    # Проверяем существование таблиц перед удалением
    if table_exists('time_selections'):
        op.drop_index(op.f('ix_time_selections_id'), table_name='time_selections')
        op.drop_table('time_selections')

    if table_exists('time_choices'):
        op.drop_index(op.f('ix_time_choices_id'), table_name='time_choices')
        op.drop_index(op.f('ix_time_choices_choice'), table_name='time_choices')
        op.drop_table('time_choices')

    if table_exists('number_selections'):
        op.drop_index(op.f('ix_number_selections_id'), table_name='number_selections')
        op.drop_table('number_selections')

    if table_exists('users'):
        op.drop_index(op.f('ix_users_username'), table_name='users')
        op.drop_index(op.f('ix_users_id'), table_name='users')
        op.drop_table('users')

    if table_exists('time_ranges'):
        op.drop_index(op.f('ix_time_ranges_time_range'), table_name='time_ranges')
        op.drop_index(op.f('ix_time_ranges_name'), table_name='time_ranges')
        op.drop_index(op.f('ix_time_ranges_id'), table_name='time_ranges')
        op.drop_table('time_ranges')

    if table_exists('numbers_choices'):
        op.drop_index(op.f('ix_numbers_choices_number'), table_name='numbers_choices')
        op.drop_index(op.f('ix_numbers_choices_id'), table_name='numbers_choices')
        op.drop_table('numbers_choices')