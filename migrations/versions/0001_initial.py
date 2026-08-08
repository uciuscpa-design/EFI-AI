"""initial persistence schema

Revision ID: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("audit_events", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("event_type", sa.String(100), nullable=False), sa.Column("actor", sa.String(100), nullable=False), sa.Column("payload", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])
    op.create_table("quotes", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("symbol", sa.String(20), nullable=False), sa.Column("bid", sa.Float(), nullable=False), sa.Column("ask", sa.Float(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_quotes_symbol", "quotes", ["symbol"])
    op.create_index("ix_quotes_created_at", "quotes", ["created_at"])
    op.create_table("orders", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("symbol", sa.String(20), nullable=False), sa.Column("side", sa.String(10), nullable=False), sa.Column("quantity", sa.Float(), nullable=False), sa.Column("reference_price", sa.Float(), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_orders_symbol", "orders", ["symbol"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_created_at", "orders", ["created_at"])


def downgrade() -> None:
    op.drop_table("orders")
    op.drop_table("quotes")
    op.drop_table("audit_events")
