from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import os
import contextvars
from dotenv import load_dotenv

# Ensure the .env configuration is loaded before checking env variables
backend_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(backend_dir, ".env")
load_dotenv(dotenv_path=env_path, override=True)

# Context variable to hold current user ID for RLS
current_user_id_var = contextvars.ContextVar("current_user_id", default="")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./local_planner.db")

# Normalize postgres:// to postgresql:// for SQLAlchemy
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def get_engine():
    if DATABASE_URL.startswith("sqlite"):
        return create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    try:
        # Test connection with a short 3s timeout to avoid startup lockup
        temp_engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 3})
        with temp_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("  [SUCCESS] PostgreSQL/Supabase connection verified successfully.")
        return temp_engine
    except Exception as e:
        print(f"  [WARNING] Supabase connection failed: {str(e)}. Falling back to local SQLite database.")
        return create_engine("sqlite:///./local_planner.db", connect_args={"check_same_thread": False})

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@event.listens_for(Session, "before_flush")
def _before_flush(session, flush_context, instances):
    user_id = session.info.get("user_id")
    if user_id:
        try:
            session.connection().info["user_id"] = str(user_id)
        except Exception:
            pass

@event.listens_for(Session, "do_orm_execute")
def _do_orm_execute(execute_state):
    # Retrieve user_id from session info (which we will set during auth)
    # and attach it to the query's execution_options which survives thread pools!
    user_id = execute_state.session.info.get("user_id")
    if user_id:
        execute_state.statement = execute_state.statement.execution_options(user_id=user_id)
        try:
            execute_state.session.connection().info["user_id"] = str(user_id)
        except Exception:
            pass

@event.listens_for(engine, 'before_cursor_execute', retval=False)
def set_rls_user_id(conn, cursor, statement, parameters, context, executemany):
    if conn.dialect.name == "postgresql":
        if "set_config" not in statement and "SET ROLE" not in statement and "RESET ROLE" not in statement:
            # Check connection metadata info first (highly robust for thread pool executions)
            user_id = conn.info.get("user_id")
            
            if not user_id and context and context.execution_options:
                user_id = context.execution_options.get("user_id")
            
            if not user_id:
                user_id = current_user_id_var.get()

            if user_id:
                cursor.execute("SELECT set_config('app.current_user_id', %s, true)", (str(user_id),))
            else:
                cursor.execute("SELECT set_config('app.current_user_id', '', true)")

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
