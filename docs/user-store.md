# User Store

SQLite-backed user persistence for RBAC. Replaces in-memory storage with persistent SQLite database.

## Overview

The user store provides persistent user storage that survives service restarts. It integrates with `RBACManager` to store user credentials, roles, and permissions.

## Database Schema

```sql
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    roles TEXT NOT NULL,        -- JSON array
    permissions TEXT NOT NULL,  -- JSON array
    created_at REAL NOT NULL,
    last_login REAL,
    active INTEGER NOT NULL DEFAULT 1
)
```

## Configuration

| Variable | Default | Description |
|---------|---------|-------------|
| `USER_STORE_BACKEND` | `sqlite` | Store backend: `sqlite` or `memory` |
| `USER_STORE_PATH` | `data/users.db` | Path to SQLite database |

## API

### `SQLiteUserStore`

```python
from core.user_store import SQLiteUserStore, get_user_store

# Singleton instance
store = get_user_store()

# Get user by ID
user = store.get("user_123")

# Get user by email
user = store.get_by_email("user@example.com")

# Save user
store.save({
    "user_id": "user_123",
    "email": "user@example.com",
    "password_hash": "bcrypt...",
    "roles": ["admin"],
    "permissions": ["read", "write"],
    "created_at": 1234567890.0,
})

# Delete user
deleted = store.delete("user_123")

# List all users
users = store.list_users()
```

## File Location

Database is stored at `data/users.db` by default. Ensure the directory exists:

```bash
mkdir -p data
```

## Password Hash Format

Uses bcrypt for password hashing. Compatible with `RBACManager`:

```python
import bcrypt

password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
```

## Migration from In-Memory

Users stored in-memory before this feature will need to be re-created. To migrate:

1. Export users from existing system (if available)
2. Re-create users via API

## Monitoring

Check user count:

```python
from core.user_store import get_user_store

store = get_user_store()
users = store.list_users()
print(f"Total users: {len(users)}")
```