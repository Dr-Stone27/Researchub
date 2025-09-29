"""add resume and profile fields to users

Revision ID: aadab32461c6
Revises: 03a45f10ea50
Create Date: 2025-09-29 16:30:57.629775

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "aadab32461c6"
down_revision: Union[str, None] = "03a45f10ea50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add resume-related fields
    op.add_column(
        "users", sa.Column("resume_url", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "users", sa.Column("resume_filename", sa.String(length=255), nullable=True)
    )
    op.add_column("users", sa.Column("resume_updated_at", sa.DateTime(), nullable=True))

    # Add profile fields
    op.add_column("users", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column(
        "users", sa.Column("profile_picture_url", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "users", sa.Column("profile_picture_updated_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "users", sa.Column("linkedin_url", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "users", sa.Column("phone_number", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "users", sa.Column("academic_level", sa.String(length=50), nullable=True)
    )
    op.add_column("users", sa.Column("graduation_year", sa.Integer(), nullable=True))
    op.add_column(
        "users", sa.Column("research_gate_url", sa.String(length=500), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # Remove the added columns in reverse order
    op.drop_column("users", "research_gate_url")
    op.drop_column("users", "graduation_year")
    op.drop_column("users", "academic_level")
    op.drop_column("users", "phone_number")
    op.drop_column("users", "linkedin_url")
    op.drop_column("users", "profile_picture_updated_at")
    op.drop_column("users", "profile_picture_url")
    op.drop_column("users", "bio")
    op.drop_column("users", "resume_updated_at")
    op.drop_column("users", "resume_filename")
    op.drop_column("users", "resume_url")
    # ### end Alembic commands ###
