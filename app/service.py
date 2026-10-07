import json
import re

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
        # 0. Check for obvious ambiguity
        # -----------------------------------------

        clarification = self.detect_ambiguous_request(
            user_request
        )

        if clarification is not None:
            return clarification

        # -----------------------------------------
        # 0.5 Check for unsupported operations
        # IMPORTANT:
        # This happens BEFORE the LLM.
        # -----------------------------------------

        unsupported_operation = (
            self.detect_unsupported_operation(
                user_request
            )
        )

        if unsupported_operation is not None:
            return unsupported_operation

        # -----------------------------------------
        # Current account state
        # -----------------------------------------

        account = self.api_client.get_account()

        if account is None:

            account_state_description = (
                "NO ACCOUNT EXISTS."
            )

        else:

            account_state_description = (
                f"AN ACCOUNT ALREADY EXISTS. "
                f"Account type: {account['account_type']}. "
                f"Balance: ₹{account['balance']}."
            )

        # -----------------------------------------
        # 1. Generate API plan using local LLM
        # -----------------------------------------

        prompt = f"""
USER REQUEST:

{user_request}

CURRENT ACCOUNT STATE:

{account_state_description}

API CATALOG:

{self.catalog_text}

Generate an API execution plan.

IMPORTANT INTENT RULES:

1. If the user wants to CREATE, OPEN, or START a new
   account, use /account/new.

2. If the user wants to CONVERT, CHANGE, SWITCH, or
   UPGRADE an EXISTING account to another account type,
   use /account/changeAccountType.

3. If an account already exists and the user says:
   - change my account
   - change to current
   - switch to current
   - convert to current
   - upgrade to current

   interpret the request as changing the existing account
   and use /account/changeAccountType.

4. If the user asks for BOTH account creation and
   account conversion in the same request, use BOTH
   APIs in the correct order:

   /account/new
   /account/deposit
   /account/changeAccountType

5. Words such as:
   - convert
   - change
   - switch
   - upgrade

   when referring to an existing account MUST use
   /account/changeAccountType.

6. A request such as:
   "convert into current account"

   means changing an existing account.

7. A request such as:
   "create a current account"

   means creating a new account.

8. A request such as:
   "create a savings account and convert it to
   current after depositing 15000"

   means:

   1. create savings account
   2. deposit 15000
   3. convert to current

9. Deposit requests must use /account/deposit.

10. Withdrawal requests must use /account/withdraw.

11. Requests asking for the current balance must use
    /account/balance.

12. Requests asking for transaction history,
    transactions, transaction details, or account history
    must use /account/transactions.

13. Requests asking for an SMS confirmation must use
    /account/notification/sms.

14. Requests asking for an email confirmation must use
    /account/notification/email.

15. NEVER use /account/deposit for a withdrawal request.

16. NEVER use /account/withdraw for a deposit request.

17. NEVER use /account/new when the user only wants to
    convert or change an existing account.

18. If the user explicitly asks to create an account
    and then convert it, /account/new is REQUIRED.

19. Only use APIs from the API catalog.

20. Never invent an API.

21. Preserve the user's requested operations.

22. Preserve the required execution order.

23. CURRENT-STATE SAFETY RULES:

    a. If CURRENT ACCOUNT STATE says an account already exists,
       do NOT use /account/new unless the user explicitly asks to
       create a NEW account.

    b. If CURRENT ACCOUNT STATE says an account already exists and
       the user asks to deposit money, use ONLY /account/deposit
       for that request. Do not create another account.

    c. If CURRENT ACCOUNT STATE says an account already exists and
       the user asks to withdraw money, use ONLY /account/withdraw
       for that request.

    d. If CURRENT ACCOUNT STATE says an account already exists and
       the user asks for balance or transactions, use the corresponding
       GET API directly. Do not create an account.

    e. If CURRENT ACCOUNT STATE says an account already exists and
       the user asks to convert/change/switch the account type, use
       /account/changeAccountType. Do not use /account/new.

24. The CURRENT ACCOUNT STATE is authoritative for whether an account
    already exists. Treat it as application state, not as part of the
    user's request.

25. For APIs that do not require parameters, use:

    "parameters": {{}}

26. Return JSON only.

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
        # 3. State-aware plan guardrail
        # -----------------------------------------
        # The local LLM is responsible for understanding the request,
        # but application state must prevent an existing account from
        # accidentally being treated as a new account.
        plan = self.repair_plan_for_existing_account(
            user_request,
            plan,
            account
        )

        # -----------------------------------------
        # 4. API validation
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
        # 5. Intent validation
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
        # 6. Account state
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
        # 7. Business rules
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
        # 8. Execute APIs
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
        # 9. Get final account state
        # -----------------------------------------

        account = self.api_client.get_account()

        # -----------------------------------------
        # 10. Create clean user response
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
    # STATE-AWARE PLAN GUARDRAIL
    # ==================================================

    def repair_plan_for_existing_account(
        self,
        user_request,
        plan,
        account
    ):
        """
        Protect the API planner from a common state-related LLM error.

        The LLM still generates the plan first. This guardrail only repairs
        an obvious single-operation mismatch when an account already exists.
        It prevents requests such as "deposit 10000" from accidentally
        becoming /account/new because the LLM forgot the current state.
        """

        if account is None:
            return plan

        request = user_request.lower().strip()

        # Do not override an explicitly requested new-account operation.
        creation_keywords = [
            "create account",
            "create an account",
            "create a new account",
            "open account",
            "open an account",
            "open a new account",
            "start an account",
            "new account"
        ]

        explicit_creation = any(
            keyword in request
            for keyword in creation_keywords
        )

        if explicit_creation:
            return plan

        # -----------------------------------------
        # Deposit
        # -----------------------------------------
        deposit_keywords = [
            "deposit",
            "deposit money",
            "put money",
            "add money",
            "add funds"
        ]

        if any(keyword in request for keyword in deposit_keywords):
            amount = self.extract_amount(user_request)

            if amount is not None:
                return {
                    "status": "success",
                    "steps": [
                        {
                            "api": "/account/deposit",
                            "parameters": {
                                "amount": amount,
                                "currency": "INR"
                            }
                        }
                    ]
                }

        # -----------------------------------------
        # Withdrawal
        # -----------------------------------------
        withdrawal_keywords = [
            "withdraw",
            "withdrawal",
            "withdraw money",
            "take money",
            "take out money",
            "cash withdrawal",
            "remove money"
        ]

        if any(keyword in request for keyword in withdrawal_keywords):
            amount = self.extract_amount(user_request)

            if amount is not None:
                return {
                    "status": "success",
                    "steps": [
                        {
                            "api": "/account/withdraw",
                            "parameters": {
                                "amount": amount,
                                "currency": "INR"
                            }
                        }
                    ]
                }

        # -----------------------------------------
        # Balance
        # -----------------------------------------
        balance_keywords = [
            "balance",
            "account balance",
            "current balance",
            "available balance",
            "how much money",
            "how much do i have"
        ]

        if any(keyword in request for keyword in balance_keywords):
            return {
                "status": "success",
                "steps": [
                    {
                        "api": "/account/balance",
                        "parameters": {}
                    }
                ]
            }

        # -----------------------------------------
        # Transaction history
        # -----------------------------------------
        transaction_keywords = [
            "transaction",
            "transactions",
            "transaction history",
            "account history",
            "transaction details",
            "transaction records",
            "show my transactions",
            "show transactions"
        ]

        if any(keyword in request for keyword in transaction_keywords):
            return {
                "status": "success",
                "steps": [
                    {
                        "api": "/account/transactions",
                        "parameters": {}
                    }
                ]
            }

        # -----------------------------------------
        # Email confirmation
        # -----------------------------------------
        if "email" in request:
            return {
                "status": "success",
                "steps": [
                    {
                        "api": "/account/notification/email",
                        "parameters": {
                            "notification_type": "confirmation"
                        }
                    }
                ]
            }

        # -----------------------------------------
        # SMS confirmation
        # -----------------------------------------
        if any(
            keyword in request
            for keyword in ["sms", "text message", "text me"]
        ):
            return {
                "status": "success",
                "steps": [
                    {
                        "api": "/account/notification/sms",
                        "parameters": {
                            "notification_type": "confirmation"
                        }
                    }
                ]
            }

        # -----------------------------------------
        # Existing-account conversion
        # -----------------------------------------
        conversion_keywords = [
            "convert",
            "conversion",
            "change account",
            "change my account",
            "change it to",
            "change it into",
            "switch account",
            "switch my account",
            "switch it to",
            "switch it into",
            "upgrade account",
            "upgrade my account",
            "upgrade it to",
            "upgrade it into"
        ]

        if any(keyword in request for keyword in conversion_keywords):
            target_type = None

            if "current" in request:
                target_type = "current"
            elif "savings" in request:
                target_type = "savings"

            if target_type is not None:
                return {
                    "status": "success",
                    "steps": [
                        {
                            "api": "/account/changeAccountType",
                            "parameters": {
                                "account_type": target_type
                            }
                        }
                    ]
                }

        return plan

    def extract_amount(self, user_request):
        """Extract a numeric amount such as 10000, 10,000 or 10K."""

        request = user_request.lower().replace(",", "")

        # Prefer values followed by k/thousand.
        match = re.search(
            r"(?:₹|rs\.?|inr\s*)?\s*(\d+(?:\.\d+)?)\s*(k|thousand)\b",
            request
        )

        if match:
            value = float(match.group(1))
            value *= 1000
            return int(value) if value.is_integer() else value

        # Standard numeric amount.
        match = re.search(
            r"(?:₹|rs\.?|inr\s*)?\s*(\d+(?:\.\d+)?)",
            request
        )

        if match:
            value = float(match.group(1))
            return int(value) if value.is_integer() else value

        return None

    # ==================================================
    # AMBIGUOUS REQUEST DETECTION
    # ==================================================

    def detect_ambiguous_request(
        self,
        user_request
    ):

        request = user_request.lower().strip()

        # -----------------------------------------
        # Check current account
        # -----------------------------------------

        account = self.api_client.get_account()

        account_exists = account is not None

        # -----------------------------------------
        # If an account already exists, requests such
        # as "change to current" can safely refer to
        # that existing account.
        # -----------------------------------------

        if account_exists:
            return None

        # -----------------------------------------
        # Explicit account creation phrases
        # -----------------------------------------

        creation_keywords = [
            "create account",
            "create an account",
            "create a new account",
            "create a savings account",
            "create a current account",
            "open account",
            "open an account",
            "open a new account",
            "open a savings account",
            "open a current account",
            "start an account",
            "new account"
        ]

        creation_requested = any(
            keyword in request
            for keyword in creation_keywords
        )

        # -----------------------------------------
        # If the user explicitly wants creation,
        # the request is not ambiguous.
        # -----------------------------------------

        if creation_requested:
            return None

        # -----------------------------------------
        # Ambiguous account-type change phrases
        # -----------------------------------------

        ambiguous_change_phrases = [

            "change to current account",
            "change into current account",
            "change to current",
            "change into current",

            "switch to current account",
            "switch into current account",
            "switch to current",
            "switch into current",

            "convert to current account",
            "convert into current account",
            "convert to current",
            "convert into current",

            "upgrade to current account",
            "upgrade into current account",
            "upgrade to current",
            "upgrade into current",

            "change to savings account",
            "change into savings account",
            "change to savings",
            "change into savings",

            "switch to savings account",
            "switch into savings account",
            "switch to savings",
            "switch into savings",

            "convert to savings account",
            "convert into savings account",
            "convert to savings",
            "convert into savings"
        ]

        ambiguous_change_requested = any(
            phrase in request
            for phrase in ambiguous_change_phrases
        )

        if ambiguous_change_requested:

            return {
                "status": "clarification_required",
                "message": (
                    "I need a little more information. "
                    "Do you want to create a new account, "
                    "or convert an existing account to "
                    "another account type?"
                )
            }

        return None

    # ==================================================
    # UNSUPPORTED OPERATION DETECTION
    # ==================================================

    def detect_unsupported_operation(
        self,
        user_request
    ):

        request = user_request.lower().strip()

        # -----------------------------------------
        # Transfer is NOT currently supported
        # by the API catalog.
        #
        # This check must happen BEFORE the LLM.
        # -----------------------------------------

        transfer_keywords = [
            "transfer",
            "transfer money",
            "transfer funds",
            "bank transfer",
            "transfer to another bank",
            "send money",
            "send funds"
        ]

        if any(
            keyword in request
            for keyword in transfer_keywords
        ):

            return {
                "status": "failed",
                "message": (
                    "The requested transfer operation "
                    "is not supported."
                )
            }

        return None

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
        # DEPOSIT INTENT
        # ==================================================

        deposit_keywords = [
            "deposit",
            "deposit money",
            "put money",
            "add money",
            "add funds"
        ]

        deposit_requested = any(
            keyword in request
            for keyword in deposit_keywords
        )

        if deposit_requested:

            if "/account/deposit" not in planned_apis:

                return (
                    False,
                    "The requested deposit operation "
                    "could not be identified."
                )

            if "/account/withdraw" in planned_apis:

                return (
                    False,
                    "The request contains a deposit operation "
                    "but the generated plan contains a withdrawal."
                )

        # ==================================================
        # WITHDRAWAL INTENT
        # ==================================================

        withdrawal_keywords = [
            "withdraw",
            "withdrawal",
            "withdraw money",
            "take money",
            "take out money",
            "cash withdrawal",
            "remove money"
        ]

        withdrawal_requested = any(
            keyword in request
            for keyword in withdrawal_keywords
        )

        if withdrawal_requested:

            if "/account/withdraw" not in planned_apis:

                return (
                    False,
                    "The requested withdrawal operation "
                    "could not be identified."
                )

            if "/account/deposit" in planned_apis:

                return (
                    False,
                    "The request contains a withdrawal operation "
                    "but the generated plan contains a deposit."
                )

        # ==================================================
        # BALANCE INTENT
        # ==================================================

        balance_keywords = [
            "balance",
            "account balance",
            "current balance",
            "available balance",
            "how much money",
            "how much do i have",
            "how much do i have in my account"
        ]

        balance_requested = any(
            keyword in request
            for keyword in balance_keywords
        )

        if balance_requested:

            if "/account/balance" not in planned_apis:

                return (
                    False,
                    "The requested balance operation "
                    "could not be identified."
                )

        # ==================================================
        # TRANSACTION HISTORY INTENT
        # ==================================================

        transaction_keywords = [
            "transaction",
            "transactions",
            "transaction history",
            "account history",
            "transaction details",
            "transaction records",
            "show my transactions",
            "show transactions"
        ]

        transaction_requested = any(
            keyword in request
            for keyword in transaction_keywords
        )

        if transaction_requested:

            if "/account/transactions" not in planned_apis:

                return (
                    False,
                    "The requested transaction history "
                    "operation could not be identified."
                )

        # ==================================================
        # SMS INTENT
        # ==================================================

        sms_keywords = [
            "sms",
            "text message",
            "text me",
            "send me a text",
            "sms confirmation",
            "text confirmation"
        ]

        sms_requested = any(
            keyword in request
            for keyword in sms_keywords
        )

        if sms_requested:

            if "/account/notification/sms" not in planned_apis:

                return (
                    False,
                    "The requested SMS notification "
                    "operation could not be identified."
                )

        # ==================================================
        # EMAIL INTENT
        # ==================================================

        email_keywords = [
            "email",
            "email confirmation",
            "send email",
            "send me an email",
            "email me"
        ]

        email_requested = any(
            keyword in request
            for keyword in email_keywords
        )

        if email_requested:

            if "/account/notification/email" not in planned_apis:

                return (
                    False,
                    "The requested email notification "
                    "operation could not be identified."
                )

        # ==================================================
        # ACCOUNT CREATION INTENT
        # ==================================================

        creation_keywords = [
            "create account",
            "create an account",
            "create a new account",
            "create a savings account",
            "create a current account",
            "open account",
            "open an account",
            "open a new account",
            "open a savings account",
            "open a current account",
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
        # ACCOUNT CONVERSION / CHANGE INTENT
        # ==================================================

        conversion_keywords = [
            "convert",
            "conversion",
            "change account",
            "change my account",
            "change it to",
            "change it into",
            "switch account",
            "switch my account",
            "switch it to",
            "switch it into",
            "upgrade account",
            "upgrade my account",
            "upgrade it to",
            "upgrade it into"
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

            # Creation + conversion is valid.
            if (
                "/account/new" in planned_apis
                and not creation_requested
            ):

                return (
                    False,
                    "An existing account conversion must "
                    "use the account change operation, not "
                    "the account creation operation."
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
                    account["account_type"].capitalize()
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

                deposit_amount = 0

                for step in plan["steps"]:

                    if step["api"] == "/account/deposit":

                        deposit_amount = (
                            step["parameters"]["amount"]
                        )

                        break

                return (
                    f"₹{deposit_amount} "
                    f"deposited successfully."
                )

        # -----------------------------------------
        # Withdrawal
        # -----------------------------------------

        if "/account/withdraw" in apis:

            if len(apis) == 1:

                return (
                    f"Withdrawal successful. "
                    f"Remaining balance: "
                    f"₹{account['balance']}."
                )

        # -----------------------------------------
        # Balance
        # -----------------------------------------

        if "/account/balance" in apis:

            if len(apis) == 1:

                return (
                    f"Your current account balance "
                    f"is ₹{account['balance']}."
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
        # SMS confirmation
        # -----------------------------------------

        if "/account/notification/sms" in apis:

            if len(apis) == 1:

                return (
                    "Confirmation SMS sent successfully."
                )

        # -----------------------------------------
        # Transaction history
        # -----------------------------------------

        if "/account/transactions" in apis:

            if len(apis) == 1:

                transactions = (
                    self.api_client.get_transactions()
                )

                if not transactions:

                    return (
                        "There are no transactions "
                        "available yet."
                    )

                return (
                    f"You have {len(transactions)} "
                    f"transaction(s) in your account."
                )

        # -----------------------------------------
        # Multi-step workflow
        # -----------------------------------------

        return (
            "Your request was completed successfully."
        )