"""Add task info to Analysis

Revision ID: dae74ff90530
Revises: 547fa0a6608b
Create Date: 2018-08-01 22:32:41.531901

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dae74ff90530'
down_revision = '547fa0a6608b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('analysis', sa.Column('finished', sa.Boolean(), nullable=True))
    op.add_column('analysis', sa.Column('task_id', sa.String(length=120), nullable=True))
    op.create_index(op.f('ix_analysis_task_id'), 'analysis', ['task_id'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_analysis_task_id'), table_name='analysis')
    op.drop_column('analysis', 'task_id')
    op.drop_column('analysis', 'finished')
    # ### end Alembic commands ###
