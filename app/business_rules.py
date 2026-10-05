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
        deposit_amount = 0

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

                # Account can either exist already
                # or be created earlier in this plan.

                if not (
                    account_exists
                    or account_created_in_plan
                ):

                    return (
                        False,
                        "Account must be created "
                        "before deposit."
                    )

                deposit_amount = params["amount"]

                # --------------------------------------------------
                # Calculate balance after this deposit
                # --------------------------------------------------

                new_balance = (
                    current_balance
                    + deposit_amount
                )

                if deposit_amount < self.MINIMUM_DEPOSIT:

                    return (
                        False,
                        "Minimum deposit is ₹10,000."
                    )

                if deposit_amount > self.MAXIMUM_DEPOSIT:

                    return (
                        False,
                        "Maximum deposit is ₹50,000."
                    )

                # Store temporary balance
                current_balance = new_balance

            # --------------------------------------------------
            # CHANGE ACCOUNT TYPE
            # --------------------------------------------------

            elif api == "/account/changeAccountType":

                # Account must already exist or be created
                # earlier in this plan.

                if not (
                    account_exists
                    or account_created_in_plan
                ):

                    return (
                        False,
                        "Account must exist before "
                        "changing account type."
                    )

                # If account existed previously,
                # check its current type.

                if account_exists:

                    if current_account_type != "savings":

                        return (
                            False,
                            "Account must currently "
                            "be a savings account."
                        )

                # If account was created in this plan,
                # it must have been savings.

                elif not savings_account:

                    return (
                        False,
                        "Account must initially "
                        "be savings."
                    )

                # --------------------------------------------------
                # Check deposit requirement
                # --------------------------------------------------

                total_balance = current_balance

                if total_balance < self.MINIMUM_DEPOSIT:

                    return (
                        False,
                        "₹10,000 deposit is required "
                        "before conversion."
                    )

                if params["account_type"] != "current":

                    return (
                        False,
                        "Only conversion to current "
                        "is allowed in this workflow."
                    )

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

        return True, "Business rules passed."