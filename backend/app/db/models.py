from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = sa.Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    firebase_uid = sa.Column(sa.Text, nullable=False, unique=True, index=True)
    email = sa.Column(sa.Text, nullable=False, unique=True)
    name = sa.Column(sa.Text, nullable=False)
    plan = sa.Column(sa.Text, nullable=False, server_default=text("'free'"))
    plan_expires_at = sa.Column(sa.TIMESTAMP(timezone=True))
    ai_messages_used = sa.Column(sa.Integer, nullable=False, server_default=text("0"))
    ai_messages_reset_at = sa.Column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    created_at = sa.Column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at = sa.Column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    categories = relationship("Category", back_populates="owner")
    __table_args__ = (
        sa.CheckConstraint("plan IN ('free', 'plus')", name="ck_user_plan"),
    )


class Category(Base):
    __tablename__ = "categories"
    id = sa.Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id = sa.Column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name = sa.Column(sa.Text, nullable=False)
    icon = sa.Column(sa.Text)
    color_hex = sa.Column(sa.Text)
    is_system = sa.Column(sa.Boolean, nullable=False, server_default=text("false"))
    created_at = sa.Column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    owner = relationship("User", back_populates="categories")


class Expense(Base):
    __tablename__ = "expenses"
    id = sa.Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id = sa.Column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id = sa.Column(
        UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=False
    )
    amount_cents = sa.Column(sa.Integer, nullable=False)
    description = sa.Column(sa.Text)
    date = sa.Column(sa.Date, nullable=False)
    input_method = sa.Column(sa.Text, nullable=False, server_default=text("'manual'"))
    receipt_url = sa.Column(sa.Text)
    voice_transcript = sa.Column(sa.Text)
    created_at = sa.Column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    __table_args__ = (
        sa.Index("idx_expenses_user_date", "user_id", sa.text("date DESC")),
        sa.Index("idx_expenses_user_category", "user_id", "category_id"),
        sa.CheckConstraint("amount_cents > 0", name="ck_expense_amount_positive"),
        sa.CheckConstraint(
            "input_method IN ('manual', 'voice', 'ocr', 'bank_sync')",
            name="ck_expense_input_method",
        ),
    )


class RecurringExpense(Base):
    __tablename__ = "recurring_expenses"
    id = sa.Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id = sa.Column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id = sa.Column(
        UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=False
    )
    amount_cents = sa.Column(sa.Integer, nullable=False)
    name = sa.Column(sa.Text, nullable=False)
    frequency = sa.Column(sa.Text, nullable=False)
    day_of_month = sa.Column(sa.Integer)
    next_due_at = sa.Column(sa.Date, nullable=False)
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=text("true"))
    created_at = sa.Column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    __table_args__ = (
        sa.Index("idx_recurring_next_due", "user_id", "next_due_at"),
        sa.CheckConstraint("amount_cents > 0", name="ck_recurring_amount_positive"),
        sa.CheckConstraint(
            "frequency IN ('monthly', 'weekly', 'annual')",
            name="ck_recurring_frequency",
        ),
        sa.CheckConstraint("day_of_month BETWEEN 1 AND 31", name="ck_recurring_day"),
    )


class Budget(Base):
    __tablename__ = "budgets"
    id = sa.Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id = sa.Column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id = sa.Column(
        UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=False
    )
    month = sa.Column(sa.Integer, nullable=False)
    year = sa.Column(sa.Integer, nullable=False)
    limit_amount_cents = sa.Column(sa.Integer, nullable=False)
    created_at = sa.Column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    __table_args__ = (
        sa.UniqueConstraint(
            "user_id",
            "category_id",
            "month",
            "year",
            name="uq_budget_user_category_month",
        ),
        sa.CheckConstraint("limit_amount_cents > 0", name="ck_budget_amount_positive"),
        sa.CheckConstraint("month BETWEEN 1 AND 12", name="ck_budget_month"),
        sa.CheckConstraint("year >= 2024", name="ck_budget_year"),
    )


class Goal(Base):
    __tablename__ = "goals"
    id = sa.Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id = sa.Column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = sa.Column(sa.Text, nullable=False)
    target_amount_cents = sa.Column(sa.Integer, nullable=False)
    deadline = sa.Column(sa.Date)
    is_active = sa.Column(sa.Boolean, nullable=False, server_default=text("true"))
    created_at = sa.Column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    __table_args__ = (
        sa.CheckConstraint("target_amount_cents > 0", name="ck_goal_amount_positive"),
    )


class GoalContribution(Base):
    __tablename__ = "goal_contributions"
    id = sa.Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id = sa.Column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    goal_id = sa.Column(
        UUID(as_uuid=True),
        sa.ForeignKey("goals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expense_id = sa.Column(
        UUID(as_uuid=True),
        sa.ForeignKey("expenses.id", ondelete="SET NULL"),
        nullable=True,
    )
    amount_cents = sa.Column(sa.Integer, nullable=False)
    source = sa.Column(sa.Text, nullable=False)
    created_at = sa.Column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    __table_args__ = (
        sa.CheckConstraint("amount_cents > 0", name="ck_contribution_amount_positive"),
        sa.CheckConstraint(
            "source IN ('manual', 'auto')", name="ck_contribution_source"
        ),
    )


class Conversation(Base):
    __tablename__ = "conversations"
    id = sa.Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id = sa.Column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id = sa.Column(sa.Text, nullable=False)
    role = sa.Column(sa.Text, nullable=False)
    content = sa.Column(sa.Text, nullable=False)
    input_method = sa.Column(sa.Text)
    created_at = sa.Column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    __table_args__ = (
        sa.Index(
            "idx_conversations_user_session",
            "user_id",
            "session_id",
            sa.text("created_at DESC"),
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant')", name="ck_conversation_role"
        ),
    )


class NotificationLog(Base):
    __tablename__ = "notification_log"
    id = sa.Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id = sa.Column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notification_type = sa.Column(
        "type",
        sa.Text,
        nullable=False,
    )
    title = sa.Column(sa.Text, nullable=False)
    message = sa.Column(sa.Text, nullable=False)
    opened = sa.Column(sa.Boolean, nullable=False, server_default=text("false"))
    sent_at = sa.Column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    __table_args__ = (
        sa.CheckConstraint(
            "type IN ('checkin', 'alert', 'budget_warning', 'goal_milestone', 'monthly_recap')",
            name="ck_notification_type",
        ),
    )
