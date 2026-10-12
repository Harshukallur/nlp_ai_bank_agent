
import pytest


@pytest.fixture(autouse=True)
def isolate_account_database(tmp_path, monkeypatch):
    """
    Give every test its own temporary SQLite database.
    Keep the application's normal account.db untouched.
    """
    test_database = tmp_path / "test_account.db"

    monkeypatch.setenv(
        "ACCOUNT_DB_PATH",
        str(test_database)
    )
