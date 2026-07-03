from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import os
import contextvars

# Context variable to hold current user ID for RLS
current_user_id_var = contextvars.ContextVar("current_user_id", default="")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./local_planner.db")

# Normalize postgres:// to postgresql:// for SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@event.listens_for(engine, 'before_cursor_execute', retval=False)
def set_rls_user_id(conn, cursor, statement, parameters, context, executemany):
    if conn.dialect.name == "postgresql":
        if "set_config" not in statement and "SET ROLE" not in statement and "RESET ROLE" not in statement:
            user_id = current_user_id_var.get()
            if user_id:
                print(f"DEBUG RLS: before_cursor_execute setting role and app.current_user_id to '{user_id}'")
                cursor.execute("SET ROLE authenticated")
                cursor.execute("SELECT set_config('app.current_user_id', %s, true)", (str(user_id),))
            else:
                print("DEBUG RLS: before_cursor_execute resetting role and clearing app.current_user_id")
                cursor.execute("RESET ROLE")
                cursor.execute("SELECT set_config('app.current_user_id', '', true)")

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
