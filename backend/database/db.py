
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DATABASE_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "cleano_campus.db"
)

DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                category TEXT NOT NULL,
                block_name TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'medium',
                priority_score INTEGER NOT NULL DEFAULT 50,
                status TEXT NOT NULL DEFAULT 'open',
                source TEXT NOT NULL DEFAULT 'manual',
                confidence REAL,
                created_at TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
                ),
                updated_at TEXT NOT NULL DEFAULT (
                    strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
                )
            )
            """
        )

    print(f"Database ready: {DATABASE_PATH}")


if __name__ == "__main__":
    init_db()
