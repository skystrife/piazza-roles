"""Add session_actions

Revision ID: 547fa0a6608b
Revises: fcdebddd1d72
Create Date: 2018-08-01 20:28:02.372157

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '547fa0a6608b'
down_revision = 'fcdebddd1d72'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('session_action',
    sa.Column('session_id', sa.Integer(), nullable=False),
    sa.Column('action_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['action_id'], ['action.id'], ),
    sa.ForeignKeyConstraint(['session_id'], ['session.id'], ),
    sa.PrimaryKeyConstraint('session_id', 'action_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('session_action')
    # ### end Alembic commands ###
