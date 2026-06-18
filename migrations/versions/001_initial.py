"""initial: create bookings table

Revision ID: 001_initial
Revises: 
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "service_type",
            sa.Enum(
                "consultation", "repair", "installation", "maintenance", "inspection",
                name="service_type_enum",
            ),
            nullable=False,
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "confirmed", "failed", "cancelled",
                name="booking_status_enum",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True, unique=True),
        sa.Column("notification_sent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("failure_reason", sa.String(1024), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_bookings_id", "bookings", ["id"])
    op.create_index("ix_bookings_status", "bookings", ["status"])


def downgrade() -> None:
    op.drop_index("ix_bookings_status", "bookings")
    op.drop_index("ix_bookings_id", "bookings")
    op.drop_table("bookings")
    op.execute("DROP TYPE IF EXISTS booking_status_enum")
    op.execute("DROP TYPE IF EXISTS service_type_enum")