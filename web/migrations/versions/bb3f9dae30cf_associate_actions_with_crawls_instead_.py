"""Associate actions with crawls instead of networks

Revision ID: bb3f9dae30cf
Revises: 4cbe8e432c6b
Create Date: 2018-07-30 23:12:43.035399

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bb3f9dae30cf'
down_revision = '4cbe8e432c6b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('action', sa.Column('crawl_id', sa.Integer(), nullable=False))
    op.drop_constraint('action_network_id_fkey', 'action', type_='foreignkey')
    op.create_foreign_key(None, 'action', 'crawl', ['crawl_id'], ['id'])
    op.drop_column('action', 'network_id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('action', sa.Column('network_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'action', type_='foreignkey')
    op.create_foreign_key('action_network_id_fkey', 'action', 'network', ['network_id'], ['id'])
    op.drop_column('action', 'crawl_id')
    # ### end Alembic commands ###