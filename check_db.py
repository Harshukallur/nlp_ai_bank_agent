import sqlite3

db_path = "data/account.db"

connection = sqlite3.connect(db_path)

tables = connection.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()

print("Database tables:")
for (table_name,) in tables:
    print(f"\n{table_name}")

    columns = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    for column in columns:
        print(column)

connection.close()