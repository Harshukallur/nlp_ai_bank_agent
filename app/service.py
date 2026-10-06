import json

from .llm import LocalLLM
from .validator import APIValidator
from .business_rules import BusinessRules
from .orchestrator import Orchestrator
from .api_client import APIClient


class AccountService:

    def __init__(self):

        print("Initializing AI Account Service...")

        self.llm = LocalLLM()

        self.catalog_path = "config/api_catalog.json"

        with open(self.catalog_path, "r") as file:
            catalog = json.load(file)

        self.catalog_text = json.dumps(
            catalog,
            indent=2
        )

        self.validator = APIValidator(
            self.catalog_path
        )

        self.business_rules = BusinessRules()

        self.api_client = APIClient()

        self.orchestrator = Orchestrator(
            self.api_client
        )

        print("AI Account Service ready.")

    # ==================================================
    # PROCESS USER REQUEST
    # ==================================================

    def process_request(self, user_request):

        # -----------------------------------------
        # 1. Generate API plan using local LLM
        # -----------------------------------------

        prompt = f"""
USER REQUEST:

{user_request}

API CATALOG:

{self.catalog_text}

Generate an API execution plan.

IMPORTANT INTENT RULES:

1. If the user wants to CREATE, OPEN, or START a new
   account, use /account/new.

2. If the user wants to CONVERT, CHANGE, SWITCH, or
   UPGRADE an EXISTING account to another account type,
   use /account/changeAccountType.

3. Words such as:
   - convert
   - change
   - switch
   - upgrade
   when referring to an existing account MUST NOT
   result in /account/new.

4. A request such as:
   "convert into current account"
   means changing the existing account type.

5. A request such as:
   "create a current account"
   means creating a new account.

6. Deposit requests must use /account/deposit.

7. Only use APIs from the API catalog.

8. Never invent an API.

9. Preserve the user's requested operation.

10. Preserve the required execution order.

11. Return JSON only.

Expected format:

{{
    "status": "success",
    "steps": [
        {{
            "api": "/endpoint",
            "parameters": {{}}
        }}
    ]
}}
"""

        response = self.llm.generate(prompt)

        # -----------------------------------------
        # 2. Parse JSON
        # -----------------------------------------

        try:

            plan = json.loads(response)

        except json.JSONDecodeError:

            return {
                "status": "failed",
                "message": (
                    "I couldn't understand the requested operation."
                )
            }

        # -----------------------------------------
        # 3. API validation
        # -----------------------------------------

        is_valid, message = self.validator.validate(
            plan
        )

        if not is_valid:

            return {
                "status": "failed",
                "message": message
            }

        # -----------------------------------------
        # 4. Intent validation
        # -----------------------------------------

        intent_valid, intent_message = (
            self.check_user_intent(
                user_request,
                plan
            )
        )

        if not intent_valid:

            return {
                "status": "failed",
                "message": intent_message
            }

        # -----------------------------------------
        # 5. Account state
        # -----------------------------------------

        account = self.api_client.get_account()

        if account is None:

            account_state = {
                "account_exists": False,
                "account_type": None,
                "balance": 0
            }

        else:

            account_state = {
                "account_exists": True,
                "account_type": account["account_type"],
                "balance": account["balance"]
            }

        # -----------------------------------------
        # 6. Business rules
        # -----------------------------------------

        business_valid, business_message = (
            self.business_rules.validate(
                plan,
                account_state
            )
        )

        if not business_valid:

            return {
                "status": "failed",
                "message": business_message
            }

        # -----------------------------------------
        # 7. Execute APIs
        # -----------------------------------------

        results = self.orchestrator.execute(
            plan
        )

        if results["status"] != "success":

            return {
                "status": "failed",
                "message": (
                    "The requested operation "
                    "could not be completed."
                )
            }

        # -----------------------------------------
        # 8. Get final account state
        # -----------------------------------------

        account = self.api_client.get_account()

        # -----------------------------------------
        # 9. Create clean user response
        # -----------------------------------------

        return {
            "status": "success",
            "message": self.create_user_message(
                plan,
                account
            ),
            "account": account
        }

    # ==================================================
    # INTENT → API CONSISTENCY VALIDATION
    # ==================================================

    def check_user_intent(
        self,
        user_request,
        plan
    ):

        request = user_request.lower().strip()

        planned_apis = [
            step.get("api")
            for step in plan.get("steps", [])
        ]

        # ==================================================
        # TRANSFER INTENT
        # ==================================================

        transfer_keywords = [
            "transfer",
            "send money",
            "send funds",
            "bank transfer",
            "transfer money"
        ]

        if any(
            keyword in request
            for keyword in transfer_keywords
        ):

            return (
                False,
                "The requested transfer operation is not supported."
            )

        # ==================================================
        # DEPOSIT INTENT
        # ==================================================

        deposit_keywords = [
            "deposit",
            "deposit money",
            "put money",
            "add money",
            "add funds"
        ]

        if any(
            keyword in request
            for keyword in deposit_keywords
        ):

            if "/account/deposit" not in planned_apis:

                return (
                    False,
                    "The requested deposit operation "
                    "could not be identified."
                )

        # ==================================================
        # ACCOUNT CONVERSION / CHANGE INTENT
        # ==================================================

        conversion_keywords = [
            "convert",
            "conversion",
            "change account",
            "change my account",
            "switch account",
            "switch my account",
            "upgrade account",
            "upgrade my account"
        ]

        conversion_requested = any(
            keyword in request
            for keyword in conversion_keywords
        )

        if conversion_requested:

            if "/account/changeAccountType" not in planned_apis:

                return (
                    False,
                    "The request appears to be an account "
                    "conversion or account-type change, but "
                    "the correct account-change operation "
                    "could not be identified."
                )

            if "/account/new" in planned_apis:

                return (
                    False,
                    "An existing account conversion must "
                    "use the account change operation, not "
                    "the account creation operation."
                )

        # ==================================================
        # ACCOUNT CREATION INTENT
        # ==================================================

        creation_keywords = [
            "create account",
            "create a new account",
            "open account",
            "open a new account",
            "start an account",
            "new account"
        ]

        creation_requested = any(
            keyword in request
            for keyword in creation_keywords
        )

        if creation_requested:

            if "/account/new" not in planned_apis:

                return (
                    False,
                    "The requested account creation "
                    "operation could not be identified."
                )

        # ==================================================
        # FINAL VALIDATION
        # ==================================================

        return (
            True,
            "Intent validation passed."
        )

    # ==================================================
    # USER-FRIENDLY RESPONSE
    # ==================================================

    def create_user_message(
        self,
        plan,
        account
    ):

        apis = [
            step["api"]
            for step in plan["steps"]
        ]

        # -----------------------------------------
        # Account creation
        # -----------------------------------------

        if "/account/new" in apis:

            if len(apis) == 1:

                account_type = (
                    account["account_type"]
                    .capitalize()
                )

                return (
                    f"{account_type} account "
                    f"created successfully."
                )

        # -----------------------------------------
        # Deposit
        # -----------------------------------------

        if "/account/deposit" in apis:

            if len(apis) == 1:

                return (
                    f"₹{account['balance']} "
                    f"deposited successfully."
                )

        # -----------------------------------------
        # Account conversion
        # -----------------------------------------

        if "/account/changeAccountType" in apis:

            if len(apis) == 1:

                return (
                    "Account type changed successfully."
                )

        # -----------------------------------------
        # Email confirmation
        # -----------------------------------------

        if "/account/notification/email" in apis:

            if len(apis) == 1:

                return (
                    "Confirmation email sent successfully."
                )

        # -----------------------------------------
        # Multi-step workflow
        # -----------------------------------------

        return (
            "Your request was completed successfully."
        )