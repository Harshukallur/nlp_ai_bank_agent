class APIClient:

    def __init__(self):

        # --------------------------------------------------
        # In-memory account state
        # --------------------------------------------------

        self.account = None

        self.next_account_id = 1001

        # Stores user-friendly activity history
        self.activity = []

        # Stores financial transaction history
        self.transactions = []

    # --------------------------------------------------
    # Get activity history
    # --------------------------------------------------

    def get_activity(self):

        return self.activity.copy()

    # --------------------------------------------------
    # Get transaction history
    # --------------------------------------------------

    def get_transactions(self):

        return self.transactions.copy()

    # --------------------------------------------------
    # API execution
    # --------------------------------------------------

    def call(self, endpoint, parameters):

        print(f"Calling {endpoint}")
        print(f"Parameters: {parameters}")

        # --------------------------------------------------
        # Create Account
        # --------------------------------------------------

        if endpoint == "/account/new":

            if self.account is not None:

                return {
                    "status": "failed",
                    "message": "An account already exists."
                }

            account_id = f"ACC{self.next_account_id}"

            self.next_account_id += 1

            self.account = {
                "account_id": account_id,
                "account_type": parameters["account_type"],
                "balance": 0,
                "currency": "INR"
            }

            # Record activity
            self.activity.append({
                "action": "Account created",
                "description": (
                    f"{parameters['account_type'].capitalize()} "
                    "account created"
                )
            })

            return {
                "status": "success",
                "message": "Account created successfully.",
                "account": self.account.copy()
            }

        # --------------------------------------------------
        # Deposit
        # --------------------------------------------------

        elif endpoint == "/account/deposit":

            if self.account is None:

                return {
                    "status": "failed",
                    "message": "No account exists."
                }

            amount = parameters["amount"]

            if amount <= 0:

                return {
                    "status": "failed",
                    "message": "Deposit amount must be greater than zero."
                }

            self.account["balance"] += amount

            # Record transaction
            self.transactions.append({
                "type": "deposit",
                "amount": amount,
                "currency": parameters["currency"],
                "balance_after": self.account["balance"]
            })

            # Record activity
            self.activity.append({
                "action": "Deposit completed",
                "description": f"₹{amount} deposited"
            })

            return {
                "status": "success",
                "message": "Deposit successful.",
                "account": self.account.copy()
            }

        # --------------------------------------------------
        # Withdraw
        # --------------------------------------------------

        elif endpoint == "/account/withdraw":

            if self.account is None:

                return {
                    "status": "failed",
                    "message": "No account exists."
                }

            amount = parameters["amount"]

            if amount <= 0:

                return {
                    "status": "failed",
                    "message": "Withdrawal amount must be greater than zero."
                }

            if amount > self.account["balance"]:

                return {
                    "status": "failed",
                    "message": "Insufficient account balance."
                }

            self.account["balance"] -= amount

            # Record transaction
            self.transactions.append({
                "type": "withdrawal",
                "amount": amount,
                "currency": parameters["currency"],
                "balance_after": self.account["balance"]
            })

            # Record activity
            self.activity.append({
                "action": "Withdrawal completed",
                "description": f"₹{amount} withdrawn"
            })

            return {
                "status": "success",
                "message": "Withdrawal successful.",
                "account": self.account.copy()
            }

        # --------------------------------------------------
        # Get Balance
        # --------------------------------------------------

        elif endpoint == "/account/balance":

            if self.account is None:

                return {
                    "status": "failed",
                    "message": "No account exists."
                }

            return {
                "status": "success",
                "message": "Balance retrieved successfully.",
                "account_id": self.account["account_id"],
                "balance": self.account["balance"],
                "currency": self.account["currency"]
            }

        # --------------------------------------------------
        # Change Account Type
        # --------------------------------------------------

        elif endpoint == "/account/changeAccountType":

            if self.account is None:

                return {
                    "status": "failed",
                    "message": "No account exists."
                }

            new_account_type = parameters["account_type"]

            old_account_type = self.account["account_type"]

            self.account["account_type"] = new_account_type

            # Record activity
            self.activity.append({
                "action": "Account converted",
                "description": (
                    f"Account converted from "
                    f"{old_account_type.capitalize()} "
                    f"to "
                    f"{new_account_type.capitalize()}"
                )
            })

            return {
                "status": "success",
                "message": "Account type changed successfully.",
                "account": self.account.copy()
            }

        # --------------------------------------------------
        # Email Confirmation
        # --------------------------------------------------

        elif endpoint == "/account/notification/email":

            if self.account is None:

                return {
                    "status": "failed",
                    "message": "No account exists."
                }

            # Record activity
            self.activity.append({
                "action": "Email confirmation sent",
                "description": "Account confirmation email sent"
            })

            return {
                "status": "success",
                "message": "Email confirmation sent.",
                "notification_type": parameters[
                    "notification_type"
                ]
            }

        # --------------------------------------------------
        # SMS Confirmation
        # --------------------------------------------------

        elif endpoint == "/account/notification/sms":

            if self.account is None:

                return {
                    "status": "failed",
                    "message": "No account exists."
                }

            # Record activity
            self.activity.append({
                "action": "SMS confirmation sent",
                "description": "Account confirmation SMS sent"
            })

            return {
                "status": "success",
                "message": "SMS confirmation sent.",
                "notification_type": parameters[
                    "notification_type"
                ]
            }

        # --------------------------------------------------
        # Transaction History
        # --------------------------------------------------

        elif endpoint == "/account/transactions":

            if self.account is None:

                return {
                    "status": "failed",
                    "message": "No account exists."
                }

            return {
                "status": "success",
                "message": "Transaction history retrieved successfully.",
                "account_id": self.account["account_id"],
                "transactions": self.transactions.copy()
            }

        # --------------------------------------------------
        # Unknown API
        # --------------------------------------------------

        else:

            return {
                "status": "failed",
                "message": f"Unsupported API: {endpoint}"
            }

    # --------------------------------------------------
    # Get current account
    # --------------------------------------------------

    def get_account(self):

        if self.account is None:

            return None

        return self.account.copy()