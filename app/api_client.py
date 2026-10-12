
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash


class APIClient:

    def __init__(self):
        base_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        data_dir = os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)

        self.db_path = os.environ.get(
            "ACCOUNT_DB_PATH",
            os.path.join(data_dir, "account.db")
        )

        self.initialize_database()

    # ======================================================
    # DATABASE
    # ======================================================

    def get_connection(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize_database(self):
        connection = self.get_connection()
        cursor = connection.cursor()

        # Users: never store plain-text passwords.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Exactly one account per user.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS account (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                account_id TEXT UNIQUE NOT NULL,
                account_type TEXT NOT NULL,
                balance REAL NOT NULL DEFAULT 0,
                currency TEXT NOT NULL DEFAULT 'INR',
                FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                balance_after REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            )
        """)

        connection.commit()
        connection.close()

    # ======================================================
    # USER REGISTRATION AND LOGIN HELPERS
    # ======================================================

    def register_user(self, username, password):
        username = username.strip()

        if not username or not password:
            return {
                "status": "failed",
                "message": "Username and password are required."
            }

        if len(password) < 8:
            return {
                "status": "failed",
                "message": "Password must be at least 8 characters."
            }

        connection = self.get_connection()

        try:
            connection.execute("""
                INSERT INTO users (username, password_hash)
                VALUES (?, ?)
            """, (
                username,
                generate_password_hash(password)
            ))
            connection.commit()

            row = connection.execute("""
                SELECT id, username FROM users
                WHERE username = ?
            """, (username,)).fetchone()

            return {
                "status": "success",
                "user": {
                    "id": row["id"],
                    "username": row["username"]
                }
            }

        except sqlite3.IntegrityError:
            return {
                "status": "failed",
                "message": "That username is already registered."
            }

        finally:
            connection.close()

    def authenticate_user(self, username, password):
        connection = self.get_connection()

        try:
            row = connection.execute("""
                SELECT id, username, password_hash
                FROM users
                WHERE username = ?
            """, (username.strip(),)).fetchone()

            if row is None or not check_password_hash(
                row["password_hash"], password
            ):
                return None

            return {
                "id": row["id"],
                "username": row["username"]
            }

        finally:
            connection.close()

    def get_user(self, user_id):
        connection = self.get_connection()

        try:
            row = connection.execute("""
                SELECT id, username
                FROM users
                WHERE id = ?
            """, (user_id,)).fetchone()

            if row is None:
                return None

            return {
                "id": row["id"],
                "username": row["username"]
            }

        finally:
            connection.close()

    # ======================================================
    # ACCOUNT HELPERS
    # ======================================================

    def get_account(self, user_id):
        if user_id is None:
            return None

        connection = self.get_connection()

        try:
            row = connection.execute("""
                SELECT account_id, account_type, balance, currency
                FROM account
                WHERE user_id = ?
            """, (user_id,)).fetchone()

            return dict(row) if row else None

        finally:
            connection.close()

    def get_activity(self, user_id):
        if user_id is None:
            return []

        connection = self.get_connection()

        try:
            rows = connection.execute("""
                SELECT action, description, created_at
                FROM activity
                WHERE user_id = ?
                ORDER BY id ASC
            """, (user_id,)).fetchall()

            return [dict(row) for row in rows]

        finally:
            connection.close()

    def get_transactions(self, user_id):
        if user_id is None:
            return []

        connection = self.get_connection()

        try:
            rows = connection.execute("""
                SELECT transaction_type, amount, currency, balance_after,
                       created_at
                FROM transactions
                WHERE user_id = ?
                ORDER BY id ASC
            """, (user_id,)).fetchall()

            return [
                {
                    "type": row["transaction_type"],
                    "amount": row["amount"],
                    "currency": row["currency"],
                    "balance_after": row["balance_after"],
                    "created_at": row["created_at"]
                }
                for row in rows
            ]

        finally:
            connection.close()

    # ======================================================
    # API EXECUTION
    # ======================================================

    def call(self, endpoint, parameters, user_id=None):
        if user_id is None or self.get_user(user_id) is None:
            return {
                "status": "failed",
                "message": "Please sign in before performing this action."
            }

        parameters = parameters or {}
        print(f"Calling {endpoint} for user_id={user_id}")

        # Load only the signed-in user's account.
        account = self.get_account(user_id)

        # --------------------------------------------------
        # CREATE ACCOUNT
        # --------------------------------------------------

        if endpoint == "/account/new":
            if account is not None:
                return {
                    "status": "failed",
                    "message": "You already have an account."
                }

            account_type = parameters.get("account_type")

            if account_type not in ("savings", "current"):
                return {
                    "status": "failed",
                    "message": "Invalid account type."
                }

            connection = self.get_connection()

            try:
                # Generate a globally unique account ID.
                row = connection.execute("""
                    SELECT COALESCE(MAX(id), 0) + 1001 AS next_number
                    FROM account
                """).fetchone()

                account_id = f"ACC{row['next_number']}"

                connection.execute("""
                    INSERT INTO account (
                        user_id, account_id, account_type, balance, currency
                    )
                    VALUES (?, ?, ?, 0, 'INR')
                """, (user_id, account_id, account_type))

                connection.execute("""
                    INSERT INTO activity (user_id, action, description)
                    VALUES (?, ?, ?)
                """, (
                    user_id,
                    "Account created",
                    f"{account_type.capitalize()} account created"
                ))

                connection.commit()

                return {
                    "status": "success",
                    "message": "Account created successfully.",
                    "account": {
                        "account_id": account_id,
                        "account_type": account_type,
                        "balance": 0,
                        "currency": "INR"
                    }
                }

            except sqlite3.IntegrityError:
                connection.rollback()
                return {
                    "status": "failed",
                    "message": "You already have an account."
                }

            finally:
                connection.close()

        # Every other banking operation requires this user's account.
        if account is None:
            return {
                "status": "failed",
                "message": "You do not have an account yet."
            }

        # --------------------------------------------------
        # DEPOSIT / WITHDRAW
        # --------------------------------------------------

        if endpoint in ("/account/deposit", "/account/withdraw"):
            amount = parameters.get("amount")

            if not isinstance(amount, (int, float)) or isinstance(amount, bool):
                return {
                    "status": "failed",
                    "message": "Please provide a valid amount."
                }

            if amount <= 0:
                return {
                    "status": "failed",
                    "message": "Amount must be greater than zero."
                }

            is_deposit = endpoint == "/account/deposit"

            if not is_deposit and amount > account["balance"]:
                return {
                    "status": "failed",
                    "message": "Insufficient account balance."
                }

            new_balance = (
                account["balance"] + amount
                if is_deposit
                else account["balance"] - amount
            )

            transaction_type = "deposit" if is_deposit else "withdrawal"
            action = "Deposit completed" if is_deposit else "Withdrawal completed"
            description = (
                f"₹{amount:g} deposited"
                if is_deposit
                else f"₹{amount:g} withdrawn"
            )

            connection = self.get_connection()

            try:
                connection.execute("""
                    UPDATE account SET balance = ?
                    WHERE user_id = ?
                """, (new_balance, user_id))

                connection.execute("""
                    INSERT INTO transactions (
                        user_id, transaction_type, amount, currency, balance_after
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    user_id,
                    transaction_type,
                    amount,
                    account["currency"],
                    new_balance
                ))

                connection.execute("""
                    INSERT INTO activity (user_id, action, description)
                    VALUES (?, ?, ?)
                """, (user_id, action, description))

                connection.commit()

            finally:
                connection.close()

            updated_account = {
                **account,
                "balance": new_balance
            }

            return {
                "status": "success",
                "message": (
                    "Deposit successful."
                    if is_deposit
                    else "Withdrawal successful."
                ),
                "account": updated_account
            }

        # --------------------------------------------------
        # GET BALANCE
        # --------------------------------------------------

        if endpoint == "/account/balance":
            return {
                "status": "success",
                "message": "Balance retrieved successfully.",
                "account_id": account["account_id"],
                "balance": account["balance"],
                "currency": account["currency"]
            }

        # --------------------------------------------------
        # CHANGE ACCOUNT TYPE
        # --------------------------------------------------

        if endpoint == "/account/changeAccountType":
            new_type = parameters.get("account_type")

            if new_type not in ("savings", "current"):
                return {
                    "status": "failed",
                    "message": "Invalid account type."
                }

            connection = self.get_connection()

            try:
                connection.execute("""
                    UPDATE account SET account_type = ?
                    WHERE user_id = ?
                """, (new_type, user_id))

                connection.execute("""
                    INSERT INTO activity (user_id, action, description)
                    VALUES (?, ?, ?)
                """, (
                    user_id,
                    "Account converted",
                    f"Account converted from {account['account_type']} to {new_type}"
                ))

                connection.commit()

            finally:
                connection.close()

            account["account_type"] = new_type

            return {
                "status": "success",
                "message": "Account type changed successfully.",
                "account": account
            }

        # --------------------------------------------------
        # EMAIL / SMS CONFIRMATION
        # --------------------------------------------------

        if endpoint in (
            "/account/notification/email",
            "/account/notification/sms"
        ):
            is_email = endpoint.endswith("/email")
            channel = "Email" if is_email else "SMS"

            connection = self.get_connection()

            try:
                connection.execute("""
                    INSERT INTO activity (user_id, action, description)
                    VALUES (?, ?, ?)
                """, (
                    user_id,
                    f"{channel} confirmation sent",
                    f"Account confirmation {channel} sent"
                ))

                connection.commit()

            finally:
                connection.close()

            return {
                "status": "success",
                "message": f"{channel} confirmation sent.",
                "notification_type": parameters.get("notification_type")
            }

        # --------------------------------------------------
        # TRANSACTION HISTORY
        # --------------------------------------------------

        if endpoint == "/account/transactions":
            return {
                "status": "success",
                "message": "Transaction history retrieved successfully.",
                "account_id": account["account_id"],
                "transactions": self.get_transactions(user_id)
            }

        return {
            "status": "failed",
            "message": f"Unsupported API: {endpoint}"
        }
