from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def gen_uuid_col(name: str = "id"):
    return sa.Column(
        name,
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )


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
    type = sa.Column(sa.Text, nullable=False)
    title = sa.Column(sa.Text, nullable=False)
    message = sa.Column(sa.Text, nullable=False)
    opened = sa.Column(sa.Boolean, nullable=False, server_default=text("false"))
    sent_at = sa.Column(
        sa.TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
