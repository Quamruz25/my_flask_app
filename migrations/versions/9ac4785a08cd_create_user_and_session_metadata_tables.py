"""Create user and session_metadata tables

Revision ID: 9ac4785a08cd
Revises: 
Create Date: 2025-04-14 13:41:05.212098

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9ac4785a08cd'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('session_metadata',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('session_id', sa.String(length=36), nullable=False),
    sa.Column('username', sa.String(length=80), nullable=False),
    sa.Column('case_number', sa.String(length=50), nullable=False),
    sa.Column('transaction_folder', sa.String(length=255), nullable=False),
    sa.Column('upload_timestamp', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('session_id')
    )
    with op.batch_alter_table('session_metadata', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_session_metadata_upload_timestamp'), ['upload_timestamp'], unique=False)
        batch_op.create_index(batch_op.f('ix_session_metadata_username'), ['username'], unique=False)

    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.Text(), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('user')
    with op.batch_alter_table('session_metadata', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_session_metadata_username'))
        batch_op.drop_index(batch_op.f('ix_session_metadata_upload_timestamp'))

    op.drop_table('session_metadata')
    # ### end Alembic commands ###
