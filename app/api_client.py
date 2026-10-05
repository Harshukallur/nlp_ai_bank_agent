class APIClient:

    def __init__(self):

        # --------------------------------------------------
        # In-memory account state
        # --------------------------------------------------

        self.account = None

        self.next_account_id = 1001

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

            self.account["balance"] += amount

            return {
                "status": "success",
                "message": "Deposit successful.",
                "account": self.account.copy()
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

            self.account["account_type"] = new_account_type

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

            return {
                "status": "success",
                "message": "Email confirmation sent.",
                "notification_type": parameters[
                    "notification_type"
                ]
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