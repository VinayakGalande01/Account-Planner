# APEX Account Planner — Multi-Tenancy Architecture Documentation

This document provides a comprehensive technical overview of the multi-tenant architecture implemented for the APEX Account Planner, explaining the database isolation, backend query scoping, AI (RAG) security context, and automatic tenant provisioning.

---

## 1. Architectural Vision

The APEX Account Planner operates on a **Logical Multi-Tenant Model** using a single shared database. Every user registers an account and belongs to their own isolated workspace (tenant). 

*   **Data Partitioning:** Every record in the database is tagged with a `user_id`.
*   **Security Principle:** Even though data lives in shared tables, users can only query, search, update, or mutate records that match their authenticated `user_id`.
*   **Runtime Context:** No global state is shared. API endpoints use request-scoped dependency injection to retrieve isolated database sessions and compute metrics dynamically.

---

## 2. Database Isolation (Supabase Postgres & RLS)

### Schema Updates
All database models in [crm_models.py](file:///e:/Account%20Planner/backend/models/crm_models.py) have been updated to include a foreign key relation to the `users` table:
```python
user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
```
This partition exists on the following tables:
*   `accounts`, `opportunities`, `contacts`, `cases`, `activities`
*   `chat_sessions`, `chat_messages`

### Row-Level Security (RLS)
To guarantee database-level isolation, Row-Level Security is enabled on Supabase Postgres. RLS acts as a database firewall that prevents unauthorized cross-tenant queries:
```sql
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
-- (Repeated for all CRM and Chat tables)
```
Policies are established on all tables to ensure that select, insert, update, and delete actions are permitted only when the row's owner matches the authenticated database context.

---

## 3. Backend Scoping & Dependency Injection (FastAPI)

### Request-Scoped Data Engine
Instead of utilizing a global in-memory data engine, FastAPI endpoints inject a request-scoped dependency `get_user_data_engine` defined in [main.py](file:///e:/Account%20Planner/backend/main.py):

```python
def get_user_data_engine(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> DataEngine:
    from models.crm_models import Account
    from sync_daemon import sync_crm_to_sqlite_for_user
    
    # Phase 1.5: Automatic Seeding on First Login
    if db.query(Account).filter(Account.user_id == current_user.id).count() == 0:
        print(f"Seeding demo data for new user: {current_user.email} (ID: {current_user.id})")
        sync_crm_to_sqlite_for_user(db, current_user.id)
        
    return DataEngine(db, current_user.id)
```

### Scoped Data Loading
The `DataEngine` in [data_engine.py](file:///e:/Account%20Planner/backend/data_engine.py) queries database tables scoped to the user session, mapping the records into local pandas DataFrames for on-the-fly tactical synthesis and health scorecard evaluations.

### Access Checks (403 Forbidden)
Endpoints fetching individual resources by ID (e.g. GET `/api/accounts/{account_id}/details`) perform validation checks to verify ownership. If the requested resource's owner does not match the active session user, a `403 Forbidden` exception is raised immediately.

---

## 4. AI & RAG Context Isolation (ChromaDB)

To prevent data leaks through semantic searches:
1.  **Metadata Tagging:** When activities are indexed into ChromaDB, the payload includes the owner's `user_id` inside the metadata tags.
2.  **Strict Filtering:** All vector queries in [vector_store.py](file:///e:/Account%20Planner/backend/vector_store.py) filter search results using ChromaDB's where metadata dictionary:
    ```python
    where_filter = {"user_id": user_id}
    ```
    This restricts semantic searches to only look at vectors belonging to the active user.

---

## 5. Sync Daemon Isolation

The sync process in [sync_daemon.py](file:///e:/Account%20Planner/backend/sync_daemon.py) is scoped with the `sync_crm_to_sqlite_for_user(db, user_id, excel_path)` function.
*   It clears previous records *only* for the active `user_id`.
*   It inserts new spreadsheet records setting their owner parameter to `user_id`.
*   It triggers local vector indexing specifically scoped to the active `user_id`.

---

## 6. How to Test & Verify

### Running Automated Checks
The test script [verify_all.py](file:///e:/Account%20Planner/backend/verify_all.py) simulates multi-tenant database creations, data hygiene checks, and isolated semantic searches. Execute it to confirm all components pass checks:
```bash
cd backend
python verify_all.py
```

### Manual Tenant Verification (Alice vs. Bob)
1.  **Register Alice:** Run a POST request to `/auth/signup` and login to obtain a JWT. Alice's dashboard automatically seeds and displays her private accounts.
2.  **Register Bob:** Open a private window, sign up Bob, and log in. Bob's dashboard seeds his own workspace.
3.  **Cross-Tenant Verification:** Have Bob query Alice's private `account_id` via `/api/accounts/{account_id}/details`. The server will return `403 Forbidden`.
