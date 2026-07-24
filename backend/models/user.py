"""
USER MODEL (models/user.py)
SQLAlchemy ORM model defining the user authentication table structure,
including unique email constraints and created_at timestamps.
"""

# --- SECTION 1: Dependencies & Base Import ---
# Imports SQLAlchemy column types and declarative base for model binding.
from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from database import Base

# --- SECTION 2: User Schema Definition ---
# Maps user entity attributes to the database 'users' table.
class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_user_email"),)

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="account_manager", nullable=False, server_default="account_manager")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

