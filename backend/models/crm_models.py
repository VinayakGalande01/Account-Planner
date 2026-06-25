from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from datetime import datetime

class Account(Base):
    __tablename__ = "accounts"

    Account_ID = Column(String, primary_key=True, index=True)
    Account_Name = Column(String, nullable=False)
    Account_Tier = Column(String)
    Industry = Column(String)
    Territory = Column(String)
    Annual_Revenue_USD = Column(Float)
    Country = Column(String)
    Health_Score = Column(Float, default=80.0)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    opportunities = relationship("Opportunity", back_populates="account", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="account", cascade="all, delete-orphan")
    cases = relationship("Case", back_populates="account", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="account", cascade="all, delete-orphan")


class Opportunity(Base):
    __tablename__ = "opportunities"

    Opp_ID = Column(String, primary_key=True, index=True)
    Account_ID = Column(String, ForeignKey("accounts.Account_ID", ondelete="CASCADE"), nullable=False)
    Opp_Name = Column(String, nullable=False)
    Amount_USD = Column(Float)
    Stage = Column(String)
    Close_Date = Column(String)
    Probability_Pct = Column(Integer)
    Competitor = Column(String)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    account = relationship("Account", back_populates="opportunities")


class Contact(Base):
    __tablename__ = "contacts"

    Contact_ID = Column(String, primary_key=True, index=True)
    Account_ID = Column(String, ForeignKey("accounts.Account_ID", ondelete="CASCADE"), nullable=False)
    First_Name = Column(String)
    Last_Name = Column(String)
    Role = Column(String)
    Department = Column(String)
    Engagement_Level = Column(String)
    Email = Column(String)
    Phone = Column(String)
    Last_Contact_Date = Column(String)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    account = relationship("Account", back_populates="contacts")
    activities = relationship("Activity", back_populates="contact")


class Case(Base):
    __tablename__ = "cases"

    Case_ID = Column(String, primary_key=True, index=True)
    Account_ID = Column(String, ForeignKey("accounts.Account_ID", ondelete="CASCADE"), nullable=False)
    Subject = Column(String)
    Status = Column(String)
    Severity = Column(String)
    CSAT_Score = Column(Float)
    Open_Date = Column(String)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    account = relationship("Account", back_populates="cases")


class Activity(Base):
    __tablename__ = "activities"

    Activity_ID = Column(String, primary_key=True, index=True)
    Account_ID = Column(String, ForeignKey("accounts.Account_ID", ondelete="CASCADE"), nullable=False)
    Contact_ID = Column(String, ForeignKey("contacts.Contact_ID", ondelete="SET NULL"), nullable=True)
    Activity_Type = Column(String)
    Type = Column(String)  # Compatibility field for 'type'
    Description = Column(Text)
    Activity_Date = Column(String)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    account = relationship("Account", back_populates="activities")
    contact = relationship("Contact", back_populates="activities")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime, default=func.now())
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String, nullable=False)  # "user" or "assistant"
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now())
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    session = relationship("ChatSession", back_populates="messages")
