"""add course_id to materials

Revision ID: 9a2f6c1d4b77
Revises: 5fdab7044942
Create Date: 2026-04-28 19:20:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9a2f6c1d4b77"
down_revision = "5fdab7044942"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("materials", schema=None) as batch_op:
        batch_op.add_column(sa.Column("course_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_materials_course_id", ["course_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_materials_course_id_courses",
            "courses",
            ["course_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table("materials", schema=None) as batch_op:
        batch_op.drop_constraint("fk_materials_course_id_courses", type_="foreignkey")
        batch_op.drop_index("ix_materials_course_id")
        batch_op.drop_column("course_id")
