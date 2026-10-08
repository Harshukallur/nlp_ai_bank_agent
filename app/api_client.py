import os
import sqlite3


class APIClient:

    def __init__(self):

        # --------------------------------------------------
        # Database path
        # --------------------------------------------------

        BASE_DIR = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )

        DATA_DIR = os.path.join(BASE_DIR, "data")

        os.makedirs(DATA_DIR, exist_ok=True)

        self.db_path = os.path.join(
            DATA_DIR,
            "account.db"
        )

        # --------------------------------------------------
        # Initialize database
        # --------------------------------------------------

        self.initialize_database()

    # ======================================================
    # DATABASE
    # ======================================================

    def get_connection(self):

        connection = sqlite3.connect(
            self.db_path
        )

        connection.row_factory = sqlite3.Row

        return connection

    # --------------------------------------------------
    # Create tables
    # --------------------------------------------------

    def initialize_database(self):

        connection = self.get_connection()

        cursor = connection.cursor()

        # --------------------------------------------------
        # Account table
        # --------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS account (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT UNIQUE NOT NULL,
                account_type TEXT NOT NULL,
                balance REAL NOT NULL DEFAULT 0,
                currency TEXT NOT NULL DEFAULT 'INR'
            )
        """)

        # --------------------------------------------------
        # Transactions table
        # --------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_type TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                balance_after REAL NOT NULL
            )
        """)

        # --------------------------------------------------
        # Activity table
        # --------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                description TEXT NOT NULL
            )
        """)

        connection.commit()

        connection.close()

    # ======================================================
    # ACTIVITY
    # ======================================================

    def get_activity(self):

        connection = self.get_connection()

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                action,
                description
            FROM activity
            ORDER BY id ASC
        """)

        rows = cursor.fetchall()

        connection.close()

        return [
            {
                "action": row["action"],
                "description": row["description"]
            }
            for row in rows
        ]

    # ======================================================
    # TRANSACTIONS
    # ======================================================

    def get_transactions(self):

        connection = self.get_connection()

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                transaction_type,
                amount,
                currency,
                balance_after
            FROM transactions
            ORDER BY id ASC
        """)

        rows = cursor.fetchall()

        connection.close()

        return [
            {
                "type": row["transaction_type"],
                "amount": row["amount"],
                "currency": row["currency"],
                "balance_after": row["balance_after"]
            }
            for row in rows
        ]

    # ======================================================
    # API EXECUTION
    # ======================================================

    def call(self, endpoint, parameters):

        print(f"Calling {endpoint}")
        print(f"Parameters: {parameters}")

        # ==================================================
        # CREATE ACCOUNT
        # ==================================================

        if endpoint == "/account/new":

            connection = self.get_connection()

            cursor = connection.cursor()

            # Check whether account already exists
            cursor.execute("""
                SELECT *
                FROM account
                LIMIT 1
            """)

            existing_account = cursor.fetchone()

            if existing_account is not None:

                connection.close()

                return {
                    "status": "failed",
                    "message": "An account already exists."
                }

            # --------------------------------------------------
            # Generate account ID
            # --------------------------------------------------

            cursor.execute("""
                SELECT account_id
                FROM account
                ORDER BY id DESC
                LIMIT 1
            """)

            last_account = cursor.fetchone()

            if last_account is None:

                account_number = 1001

            else:

                previous_id = last_account["account_id"]

                account_number = (
                    int(previous_id.replace("ACC", "")) + 1
                )

            account_id = f"ACC{account_number}"

            account_type = parameters["account_type"]

            # --------------------------------------------------
            # Insert account
            # --------------------------------------------------

            cursor.execute("""
                INSERT INTO account (
                    account_id,
                    account_type,
                    balance,
                    currency
                )
                VALUES (?, ?, ?, ?)
            """, (
                account_id,
                account_type,
                0,
                "INR"
            ))

            # --------------------------------------------------
            # Record activity
            # --------------------------------------------------

            cursor.execute("""
                INSERT INTO activity (
                    action,
                    description
                )
                VALUES (?, ?)
            """, (
                "Account created",
                f"{account_type.capitalize()} account created"
            ))

            connection.commit()

            connection.close()

            account = {
                "account_id": account_id,
                "account_type": account_type,
                "balance": 0,
                "currency": "INR"
            }

            return {
                "status": "success",
                "message": "Account created successfully.",
                "account": account
            }

        # ==================================================
        # DEPOSIT
        # ==================================================

        elif endpoint == "/account/deposit":

            connection = self.get_connection()

            cursor = connection.cursor()

            cursor.execute("""
                SELECT *
                FROM account
                LIMIT 1
            """)

            account = cursor.fetchone()

            if account is None:

                connection.close()

                return {
                    "status": "failed",
                    "message": "No account exists."
                }

            amount = parameters["amount"]

            if amount <= 0:

                connection.close()

                return {
                    "status": "failed",
                    "message": "Deposit amount must be greater than zero."
                }

            new_balance = account["balance"] + amount

            # --------------------------------------------------
            # Update balance
            # --------------------------------------------------

            cursor.execute("""
                UPDATE account
                SET balance = ?
                WHERE account_id = ?
            """, (
                new_balance,
                account["account_id"]
            ))

            # --------------------------------------------------
            # Record transaction
            # --------------------------------------------------

            cursor.execute("""
                INSERT INTO transactions (
                    transaction_type,
                    amount,
                    currency,
                    balance_after
                )
                VALUES (?, ?, ?, ?)
            """, (
                "deposit",
                amount,
                parameters["currency"],
                new_balance
            ))

            # --------------------------------------------------
            # Record activity
            # --------------------------------------------------

            cursor.execute("""
                INSERT INTO activity (
                    action,
                    description
                )
                VALUES (?, ?)
            """, (
                "Deposit completed",
                f"₹{amount} deposited"
            ))

            connection.commit()

            connection.close()

            updated_account = {
                "account_id": account["account_id"],
                "account_type": account["account_type"],
                "balance": new_balance,
                "currency": account["currency"]
            }

            return {
                "status": "success",
                "message": "Deposit successful.",
                "account": updated_account
            }

        # ==================================================
        # WITHDRAW
        # ==================================================

        elif endpoint == "/account/withdraw":

            connection = self.get_connection()

            cursor = connection.cursor()

            cursor.execute("""
                SELECT *
                FROM account
                LIMIT 1
            """)

            account = cursor.fetchone()

            if account is None:

                connection.close()

                return {
                    "status": "failed",
                    "message": "No account exists."
                }

            amount = parameters["amount"]

            if amount <= 0:

                connection.close()

                return {
                    "status": "failed",
                    "message": "Withdrawal amount must be greater than zero."
                }

            if amount > account["balance"]:

                connection.close()

                return {
                    "status": "failed",
                    "message": "Insufficient account balance."
                }

            new_balance = account["balance"] - amount

            # --------------------------------------------------
            # Update balance
            # --------------------------------------------------

            cursor.execute("""
                UPDATE account
                SET balance = ?
                WHERE account_id = ?
            """, (
                new_balance,
                account["account_id"]
            ))

            # --------------------------------------------------
            # Record transaction
            # --------------------------------------------------

            cursor.execute("""
                INSERT INTO transactions (
                    transaction_type,
                    amount,
                    currency,
                    balance_after
                )
                VALUES (?, ?, ?, ?)
            """, (
                "withdrawal",
                amount,
                parameters["currency"],
                new_balance
            ))

            # --------------------------------------------------
            # Record activity
            # --------------------------------------------------

            cursor.execute("""
                INSERT INTO activity (
                    action,
                    description
                )
                VALUES (?, ?)
            """, (
                "Withdrawal completed",
                f"₹{amount} withdrawn"
            ))

            connection.commit()

            connection.close()

            updated_account = {
                "account_id": account["account_id"],
                "account_type": account["account_type"],
                "balance": new_balance,
                "currency": account["currency"]
            }

            return {
                "status": "success",
                "message": "Withdrawal successful.",
                "account": updated_account
            }

        # ==================================================
        # GET BALANCE
        # ==================================================

        elif endpoint == "/account/balance":

            account = self.get_account()

            if account is None:

                return {
                    "status": "failed",
                    "message": "No account exists."
                }

            return {
                "status": "success",
                "message": "Balance retrieved successfully.",
                "account_id": account["account_id"],
                "balance": account["balance"],
                "currency": account["currency"]
            }

        # ==================================================
        # CHANGE ACCOUNT TYPE
        # ==================================================

        elif endpoint == "/account/changeAccountType":

            connection = self.get_connection()

            cursor = connection.cursor()

            cursor.execute("""
                SELECT *
                FROM account
                LIMIT 1
            """)

            account = cursor.fetchone()

            if account is None:

                connection.close()

                return {
                    "status": "failed",
                    "message": "No account exists."
                }

            new_account_type = parameters["account_type"]

            old_account_type = account["account_type"]

            # --------------------------------------------------
            # Update account type
            # --------------------------------------------------

            cursor.execute("""
                UPDATE account
                SET account_type = ?
                WHERE account_id = ?
            """, (
                new_account_type,
                account["account_id"]
            ))

            # --------------------------------------------------
            # Record activity
            # --------------------------------------------------

            cursor.execute("""
                INSERT INTO activity (
                    action,
                    description
                )
                VALUES (?, ?)
            """, (
                "Account converted",
                (
                    f"Account converted from "
                    f"{old_account_type.capitalize()} "
                    f"to "
                    f"{new_account_type.capitalize()}"
                )
            ))

            connection.commit()

            connection.close()

            updated_account = {
                "account_id": account["account_id"],
                "account_type": new_account_type,
                "balance": account["balance"],
                "currency": account["currency"]
            }

            return {
                "status": "success",
                "message": "Account type changed successfully.",
                "account": updated_account
            }

        # ==================================================
        # EMAIL CONFIRMATION
        # ==================================================

        elif endpoint == "/account/notification/email":

            account = self.get_account()

            if account is None:

                return {
                    "status": "failed",
                    "message": "No account exists."
                }

            connection = self.get_connection()

            cursor = connection.cursor()

            cursor.execute("""
                INSERT INTO activity (
                    action,
                    description
                )
                VALUES (?, ?)
            """, (
                "Email confirmation sent",
                "Account confirmation email sent"
            ))

            connection.commit()

            connection.close()

            return {
                "status": "success",
                "message": "Email confirmation sent.",
                "notification_type": parameters[
                    "notification_type"
                ]
            }

        # ==================================================
        # SMS CONFIRMATION
        # ==================================================

        elif endpoint == "/account/notification/sms":

            account = self.get_account()

            if account is None:

                return {
                    "status": "failed",
                    "message": "No account exists."
                }

            connection = self.get_connection()

            cursor = connection.cursor()

            cursor.execute("""
                INSERT INTO activity (
                    action,
                    description
                )
                VALUES (?, ?)
            """, (
                "SMS confirmation sent",
                "Account confirmation SMS sent"
            ))

            connection.commit()

            connection.close()

            return {
                "status": "success",
                "message": "SMS confirmation sent.",
                "notification_type": parameters[
                    "notification_type"
                ]
            }

        # ==================================================
        # TRANSACTION HISTORY
        # ==================================================

        elif endpoint == "/account/transactions":

            account = self.get_account()

            if account is None:

                return {
                    "status": "failed",
                    "message": "No account exists."
                }

            return {
                "status": "success",
                "message": (
                    "Transaction history retrieved successfully."
                ),
                "account_id": account["account_id"],
                "transactions": self.get_transactions()
            }

        # ==================================================
        # UNKNOWN API
        # ==================================================

        else:

            return {
                "status": "failed",
                "message": f"Unsupported API: {endpoint}"
            }

    # ======================================================
    # GET CURRENT ACCOUNT
    # ======================================================

    def get_account(self):

        connection = self.get_connection()

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                account_id,
                account_type,
                balance,
                currency
            FROM account
            LIMIT 1
        """)

        row = cursor.fetchone()

        connection.close()

        if row is None:

            return None

        return {
            "account_id": row["account_id"],
            "account_type": row["account_type"],
            "balance": row["balance"],
            "currency": row["currency"]
        }