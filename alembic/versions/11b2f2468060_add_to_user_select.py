"""Add to user select

Revision ID: 11b2f2468060
Revises: cea8f943d07d
Create Date: 2024-11-10 16:29:14.955017

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11b2f2468060'
down_revision: Union[str, None] = 'cea8f943d07d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
