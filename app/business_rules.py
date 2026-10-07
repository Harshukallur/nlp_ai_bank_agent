class BusinessRules:

    MINIMUM_DEPOSIT = 10000
    MAXIMUM_DEPOSIT = 50000

    def validate(self, plan, account_state=None):

        # --------------------------------------------------
        # Account state from previous requests
        # --------------------------------------------------

        if account_state is None:
            account_state = {}

        account_exists = account_state.get(
            "account_exists",
            False
        )

        current_account_type = account_state.get(
            "account_type"
        )

        current_balance = account_state.get(
            "balance",
            0
        )

        # --------------------------------------------------
        # Temporary state for this plan
        # --------------------------------------------------

        account_created_in_plan = False
        savings_account = False

        # --------------------------------------------------
        # Process each step
        # --------------------------------------------------

        for step in plan["steps"]:

            api = step["api"]
            params = step["parameters"]

            # --------------------------------------------------
            # CREATE ACCOUNT
            # --------------------------------------------------

            if api == "/account/new":

                if account_exists:
                    return (
                        False,
                        "An account already exists."
                    )

                if params["account_type"] != "savings":
                    return (
                        False,
                        "Account must initially "
                        "be a savings account."
                    )

                account_created_in_plan = True
                savings_account = True

            # --------------------------------------------------
            # DEPOSIT
            # --------------------------------------------------

            elif api == "/account/deposit":

                if not (
                    account_exists
                    or account_created_in_plan
                ):
                    return (
                        False,
                        "Account must be created "
                        "before deposit."
                    )

                amount = params["amount"]

                # Deposit amount must be positive
                if amount <= 0:
                    return (
                        False,
                        "Deposit amount must be "
                        "greater than zero."
                    )

                # Minimum deposit
                if amount < self.MINIMUM_DEPOSIT:
                    return (
                        False,
                        "Minimum deposit is ₹10,000."
                    )

                # Maximum deposit
                if amount > self.MAXIMUM_DEPOSIT:
                    return (
                        False,
                        "Maximum deposit is ₹50,000."
                    )

                # Update temporary balance
                current_balance += amount

            # --------------------------------------------------
            # WITHDRAW
            # --------------------------------------------------

            elif api == "/account/withdraw":

                if not (
                    account_exists
                    or account_created_in_plan
                ):
                    return (
                        False,
                        "Account must be created "
                        "before withdrawal."
                    )

                amount = params["amount"]

                # Withdrawal amount must be positive
                if amount <= 0:
                    return (
                        False,
                        "Withdrawal amount must be "
                        "greater than zero."
                    )

                # Check sufficient balance
                if amount > current_balance:
                    return (
                        False,
                        "Insufficient account balance."
                    )

                # Update temporary balance
                current_balance -= amount

            # --------------------------------------------------
            # GET BALANCE
            # --------------------------------------------------

            elif api == "/account/balance":

                if not (
                    account_exists
                    or account_created_in_plan
                ):
                    return (
                        False,
                        "Account must exist before "
                        "checking balance."
                    )

                # No state modification required.
                # current_balance represents the
                # balance at this point in the plan.

            # --------------------------------------------------
            # CHANGE ACCOUNT TYPE
            # --------------------------------------------------

            elif api == "/account/changeAccountType":

                if not (
                    account_exists
                    or account_created_in_plan
                ):
                    return (
                        False,
                        "Account must exist before "
                        "changing account type."
                    )

                # --------------------------------------------------
                # Existing account
                # --------------------------------------------------

                if account_exists:

                    if current_account_type != "savings":
                        return (
                            False,
                            "Account must currently "
                            "be a savings account."
                        )

                # --------------------------------------------------
                # Account created in this plan
                # --------------------------------------------------

                elif not savings_account:

                    return (
                        False,
                        "Account must initially "
                        "be savings."
                    )

                # --------------------------------------------------
                # Check deposit requirement
                # --------------------------------------------------

                if current_balance < self.MINIMUM_DEPOSIT:
                    return (
                        False,
                        "₹10,000 deposit is required "
                        "before conversion."
                    )

                # --------------------------------------------------
                # Only savings → current is allowed
                # --------------------------------------------------

                if params["account_type"] != "current":
                    return (
                        False,
                        "Only conversion to current "
                        "is allowed in this workflow."
                    )

                # Update temporary account type
                current_account_type = "current"

            # --------------------------------------------------
            # EMAIL CONFIRMATION
            # --------------------------------------------------

            elif api == "/account/notification/email":

                if not (
                    account_exists
                    or account_created_in_plan
                ):
                    return (
                        False,
                        "Account must exist before "
                        "sending confirmation email."
                    )

            # --------------------------------------------------
            # SMS CONFIRMATION
            # --------------------------------------------------

            elif api == "/account/notification/sms":

                if not (
                    account_exists
                    or account_created_in_plan
                ):
                    return (
                        False,
                        "Account must exist before "
                        "sending confirmation SMS."
                    )

            # --------------------------------------------------
            # TRANSACTION HISTORY
            # --------------------------------------------------

            elif api == "/account/transactions":

                if not (
                    account_exists
                    or account_created_in_plan
                ):
                    return (
                        False,
                        "Account must exist before "
                        "checking transaction history."
                    )

        # --------------------------------------------------
        # All business rules passed
        # --------------------------------------------------

        return True, "Business rules passed."