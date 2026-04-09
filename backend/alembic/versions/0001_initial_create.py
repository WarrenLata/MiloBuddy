"""initial create

Revision ID: 0001_initial_create
Revises:
Create Date: 2026-04-09 00:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial_create"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # users
    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        sa.Column("firebase_uid", sa.Text(), nullable=False, unique=True),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("plan", sa.Text(), nullable=False, server_default=text("'free'")),
        sa.Column("plan_expires_at", sa.TIMESTAMP(timezone=True)),
        sa.Column(
            "ai_messages_used", sa.Integer(), nullable=False, server_default=text("0")
        ),
        sa.Column(
            "ai_messages_reset_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
    )
    op.create_index("idx_users_firebase_uid", "users", ["firebase_uid"])

    # categories
    op.create_table(
        "categories",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("icon", sa.Text()),
        sa.Column("color_hex", sa.Text()),
        sa.Column(
            "is_system", sa.Boolean(), nullable=False, server_default=text("false")
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
    )
    op.create_index("idx_categories_user_id", "categories", ["user_id"])

    # expenses
    op.create_table(
        "expenses",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("categories.id"),
            nullable=False,
        ),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "input_method", sa.Text(), nullable=False, server_default=text("'manual'")
        ),
        sa.Column("receipt_url", sa.Text()),
        sa.Column("voice_transcript", sa.Text()),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
    )
    op.create_index("idx_expenses_user_id", "expenses", ["user_id"])
    op.create_index("idx_expenses_user_date", "expenses", ["user_id", "date"])
    op.create_index(
        "idx_expenses_user_category", "expenses", ["user_id", "category_id"]
    )
    op.create_index(
        "idx_expenses_user_month", "expenses", [sa.text("date_trunc('month', date)")]
    )

    # recurring_expenses
    op.create_table(
        "recurring_expenses",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("categories.id"),
            nullable=False,
        ),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("frequency", sa.Text(), nullable=False),
        sa.Column("day_of_month", sa.Integer()),
        sa.Column("next_due_at", sa.Date(), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=text("true")
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
    )
    op.create_index("idx_recurring_user_id", "recurring_expenses", ["user_id"])
    op.create_index(
        "idx_recurring_next_due", "recurring_expenses", ["user_id", "next_due_at"]
    )

    # budgets
    op.create_table(
        "budgets",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("categories.id"),
            nullable=False,
        ),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("limit_amount_cents", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
    )
    op.create_index("idx_budgets_user_id", "budgets", ["user_id"])
    op.create_index("idx_budgets_user_month", "budgets", ["user_id", "year", "month"])
    op.create_unique_constraint(
        "uq_budget_user_category_month",
        "budgets",
        ["user_id", "category_id", "month", "year"],
    )

    # goals
    op.create_table(
        "goals",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("target_amount_cents", sa.Integer(), nullable=False),
        sa.Column("deadline", sa.Date()),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=text("true")
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
    )
    op.create_index("idx_goals_user_id", "goals", ["user_id"])

    # goal_contributions
    op.create_table(
        "goal_contributions",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "goal_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("goals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "expense_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("expenses.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
    )
    op.create_index("idx_goal_contributions_user_id", "goal_contributions", ["user_id"])
    op.create_index("idx_goal_contributions_goal_id", "goal_contributions", ["goal_id"])

    # conversations
    op.create_table(
        "conversations",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("input_method", sa.Text()),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
    )
    op.create_index(
        "idx_conversations_user_session",
        "conversations",
        ["user_id", "session_id", "created_at"],
    )
    op.create_index(
        "idx_conversations_user_recent", "conversations", ["user_id", "created_at"]
    )

    # notification_log
    op.create_table(
        "notification_log",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("opened", sa.Boolean(), nullable=False, server_default=text("false")),
        sa.Column(
            "sent_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
    )
    op.create_index("idx_notification_log_user_id", "notification_log", ["user_id"])
    op.create_index(
        "idx_notification_log_user_recent", "notification_log", ["user_id", "sent_at"]
    )

    # Seed system categories
    op.execute("""
    INSERT INTO categories (id, user_id, name, icon, color_hex, is_system) VALUES
        (gen_random_uuid(), NULL, 'Alimentation',   '🛒', '#1D9E75', true),
        (gen_random_uuid(), NULL, 'Restaurants',    '🍽️', '#EF9F27', true),
        (gen_random_uuid(), NULL, 'Transport',      '🚗', '#378ADD', true),
        (gen_random_uuid(), NULL, 'Logement',       '🏠', '#7F77DD', true),
        (gen_random_uuid(), NULL, 'Santé',          '💊', '#E24B4A', true),
        (gen_random_uuid(), NULL, 'Loisirs',        '🎬', '#D4537E', true),
        (gen_random_uuid(), NULL, 'Vêtements',      '👕', '#D85A30', true),
        (gen_random_uuid(), NULL, 'Enfants',        '👶', '#639922', true),
        (gen_random_uuid(), NULL, 'Épargne',        '💰', '#085041', true),
        (gen_random_uuid(), NULL, 'Autre',          '📦', '#888780', true);
    """)

    # Trigger to update updated_at on users
    op.execute("""
    CREATE OR REPLACE FUNCTION trigger_set_timestamp()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = now();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER set_timestamp
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_set_timestamp();
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS set_timestamp ON users")
    op.execute("DROP FUNCTION IF EXISTS trigger_set_timestamp()")
    op.execute("DELETE FROM categories WHERE is_system = true")
    op.drop_index("idx_notification_log_user_recent", table_name="notification_log")
    op.drop_index("idx_notification_log_user_id", table_name="notification_log")
    op.drop_table("notification_log")
    op.drop_index("idx_conversations_user_recent", table_name="conversations")
    op.drop_index("idx_conversations_user_session", table_name="conversations")
    op.drop_table("conversations")
    op.drop_index("idx_goal_contributions_goal_id", table_name="goal_contributions")
    op.drop_index("idx_goal_contributions_user_id", table_name="goal_contributions")
    op.drop_table("goal_contributions")
    op.drop_index("idx_goals_user_id", table_name="goals")
    op.drop_table("goals")
    op.drop_constraint("uq_budget_user_category_month", "budgets", type_="unique")
    op.drop_index("idx_budgets_user_month", table_name="budgets")
    op.drop_index("idx_budgets_user_id", table_name="budgets")
    op.drop_table("budgets")
    op.drop_index("idx_recurring_next_due", table_name="recurring_expenses")
    op.drop_index("idx_recurring_user_id", table_name="recurring_expenses")
    op.drop_table("recurring_expenses")
    op.drop_index("idx_expenses_user_month", table_name="expenses")
    op.drop_index("idx_expenses_user_category", table_name="expenses")
    op.drop_index("idx_expenses_user_date", table_name="expenses")
    op.drop_index("idx_expenses_user_id", table_name="expenses")
    op.drop_table("expenses")
    op.drop_index("idx_categories_user_id", table_name="categories")
    op.drop_table("categories")
    op.drop_index("idx_users_firebase_uid", table_name="users")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
