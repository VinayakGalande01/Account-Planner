import pytest
from sqlalchemy import text
from dotenv import load_dotenv
# Load environment variables before importing database modules
load_dotenv(override=True)
from database import SessionLocal, current_user_id_var, DATABASE_URL
from models.user import User
from models.crm_models import Account

def test_rls_multi_tenancy_isolation():
    # Only run on PostgreSQL because SQLite doesn't support RLS
    if not DATABASE_URL.startswith("postgresql"):
        pytest.skip("Skipping RLS test on non-PostgreSQL database")

    db = SessionLocal()
    print(f"DEBUG TEST: current_user_id_var id={id(current_user_id_var)}")
    try:
        # 1. Clean up/setup test users if they exist
        db.query(Account).filter(Account.Account_ID.in_(["test_acc_a", "test_acc_b"])).delete()
        db.query(User).filter(User.email.in_(["user_a@test.com", "user_b@test.com"])).delete()
        db.commit()

        # Create two test users
        from auth.password import hash_password
        user_a = User(name="User A", email="user_a@test.com", hashed_password=hash_password("pw"))
        user_b = User(name="User B", email="user_b@test.com", hashed_password=hash_password("pw"))
        db.add_all([user_a, user_b])
        db.commit()
        db.refresh(user_a)
        db.refresh(user_b)
        user_a_id = user_a.id
        user_b_id = user_b.id
        db.commit()

        # 2. Authenticate as User A and insert an account
        current_user_id_var.set(str(user_a_id))
        # Verify RLS session setting is loaded correctly in transaction
        res = db.execute(text("SELECT current_setting('app.current_user_id', true)")).scalar()
        assert res == str(user_a_id)

        acc_a = Account(
            Account_ID="test_acc_a",
            Account_Name="Acme Tenant A",
            Account_Tier="Tier 1",
            Industry="Software",
            Territory="US",
            Annual_Revenue_USD=1000000.0,
            Country="US",
            Health_Score=90.0,
            user_id=user_a_id
        )
        db.add(acc_a)
        db.commit()

        # 3. Authenticate as User B
        current_user_id_var.set(str(user_b_id))
        res = db.execute(text("SELECT current_setting('app.current_user_id', true)")).scalar()
        assert res == str(user_b_id)

        # 4. Attempt to read User A's account while logged in as User B
        # RLS should filter this row out entirely
        accs = db.query(Account).filter(Account.Account_ID == "test_acc_a").all()
        assert len(accs) == 0, "RLS failed: User B was able to read User A's account!"

        # 5. Attempt to insert a record with user_id = User A while logged in as User B
        # This should fail because of WITH CHECK clause in the RLS policy!
        bad_acc = Account(
            Account_ID="test_acc_b",
            Account_Name="Beta Tenant B",
            Account_Tier="Tier 2",
            Industry="Hardware",
            Territory="EU",
            Annual_Revenue_USD=50000.0,
            Country="FR",
            Health_Score=85.0,
            user_id=user_a_id  # Bad user_id mapping
        )
        db.add(bad_acc)
        
        with pytest.raises(Exception) as excinfo:
            db.commit()
        db.rollback()
        assert "insufficient_privilege" in str(excinfo.value).lower() or "row level security policy" in str(excinfo.value).lower() or "violates row-level security policy" in str(excinfo.value).lower()

        # Clean up
        current_user_id_var.set("")
        db.query(Account).filter(Account.Account_ID.in_(["test_acc_a", "test_acc_b"])).delete()
        db.query(User).filter(User.email.in_(["user_a@test.com", "user_b@test.com"])).delete()
        db.commit()

    finally:
        db.close()
