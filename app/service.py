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

        with open(self.catalog_path, "r", encoding="utf-8") as file:
            catalog = json.load(file)

        self.catalog_text = json.dumps(catalog, indent=2)

        self.validator = APIValidator(self.catalog_path)
        self.business_rules = BusinessRules()
        self.api_client = APIClient()
        self.orchestrator = Orchestrator(self.api_client)

        print("AI Account Service ready.")

    # ==================================================
    # PROCESS USER REQUEST
    # ==================================================

    def process_request(self, user_request, user_id):
        if user_id is None or self.api_client.get_user(user_id) is None:
            return {
                "status": "failed",
                "message": "Please sign in before continuing."
            }

        request = user_request.lower().strip()

        if not request:
            return {
                "status": "failed",
                "message": "Please enter a request."
            }

        clarification = self.detect_ambiguous_request(
            request, user_id
        )
        if clarification is not None:
            return clarification

        unsupported = self.detect_unsupported_operation(request)
        if unsupported is not None:
            return unsupported

        account = self.api_client.get_account(user_id)

        # --------------------------------------------------
        # DETERMINISTIC ACCOUNT CREATION
        # --------------------------------------------------
        # Explicit creation requests bypass the LLM.
        # Creating an account does not require a deposit.
        if self.is_account_creation_request(request):

            if account is not None:
                return {
                    "status": "failed",
                    "message": (
                        "You already have an account. "
                        "Each user can have only one bank account."
                    )
                }

            target_type = self.extract_account_type(request)

            if target_type is None:
                return {
                    "status": "clarification_required",
                    "message": (
                        "Would you like to create a savings "
                        "account or a current account?"
                    )
                }

            plan = {
                "status": "success",
                "steps": [
                    {
                        "api": "/account/new",
                        "parameters": {
                            "account_type": target_type
                        }
                    }
                ]
            }

        else:
            if account is None and self.requires_existing_account(request):
                return {
                    "status": "failed",
                    "message": (
                        "Please create a savings or current account "
                        "before performing this operation."
                    )
                }

            account_state_description = (
                "NO ACCOUNT EXISTS FOR THIS USER."
                if account is None
                else (
                    "THIS USER ALREADY HAS AN ACCOUNT. "
                    f"Account type: {account['account_type']}. "
                    f"Balance: INR {account['balance']}."
                )
            )

            prompt = f"""
USER REQUEST:
{user_request}

CURRENT ACCOUNT STATE:
{account_state_description}

API CATALOG:
{self.catalog_text}

Generate a JSON API execution plan using only this catalog.

INTENT RULES:
1. Create an account using /account/new.
2. Deposit using /account/deposit.
3. Withdraw using /account/withdraw.
4. Get balance using /account/balance.
5. Change account type using /account/changeAccountType.
6. Email confirmation uses /account/notification/email.
7. SMS confirmation uses /account/notification/sms.
8. Transaction history uses /account/transactions.
9. Never invent endpoints, parameters, IDs, or account details.
10. Never confuse deposits with withdrawals.
11. Never create a second account for an existing user.
12. Use the execution order requested by the user.
13. Do not invent missing amounts or account types.
14. APIs without parameters must use an empty parameters object.
15. Return only a JSON object in this format:
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

            try:
                response = self.llm.generate(prompt)
                plan = json.loads(response)
            except (ValueError, json.JSONDecodeError, TypeError):
                return {
                    "status": "failed",
                    "message": (
                        "I couldn't safely interpret your request. "
                        "Please rephrase it and try again."
                    )
                }

            if not isinstance(plan, dict):
                return {
                    "status": "failed",
                    "message": "The generated API plan is invalid."
                }

            plan = self.repair_plan_for_existing_account(
                user_request, plan, account
            )

        # --------------------------------------------------
        # VALIDATE BEFORE EXECUTION
        # --------------------------------------------------

        is_valid, message = self.validator.validate(plan)
        if not is_valid:
            return {
                "status": "failed",
                "message": message
            }

        intent_valid, intent_message = self.check_user_intent(
            user_request, plan
        )
        if not intent_valid:
            return {
                "status": "failed",
                "message": intent_message
            }

        # Re-read this authenticated user's account.
        account = self.api_client.get_account(user_id)

        account_state = {
            "account_exists": account is not None,
            "account_type": account["account_type"] if account else None,
            "balance": account["balance"] if account else 0
        }

        business_valid, business_message = self.business_rules.validate(
            plan, account_state
        )
        if not business_valid:
            return {
                "status": "failed",
                "message": business_message
            }

        # Only the authenticated user's ID is passed to execution.
        results = self.orchestrator.execute(
            plan, user_id=user_id
        )

        if results.get("status") != "success":
            failed_results = results.get("results", [])
            failed_message = (
                "The requested operation could not be completed."
            )

            if failed_results:
                last_result = failed_results[-1].get("result", {})
                if isinstance(last_result, dict):
                    failed_message = last_result.get(
                        "message", failed_message
                    )

            return {
                "status": "failed",
                "message": failed_message,
                "results": failed_results
            }

        account = self.api_client.get_account(user_id)

        return {
            "status": "success",
            "message": self.create_user_message(
                plan, account, user_id
            ),
            "account": account
        }

    # ==================================================
    # ACCOUNT CREATION HELPERS
    # ==================================================

    def is_account_creation_request(self, request):
        patterns = [
            r"\bcreate\s+(?:(?:a|an)\s+)?(?:new\s+)?(?:(?:savings|current)\s+)?account\b",
            r"\bopen\s+(?:(?:a|an)\s+)?(?:new\s+)?(?:(?:savings|current)\s+)?account\b",
            r"\bstart\s+(?:(?:a|an)\s+)?(?:new\s+)?(?:(?:savings|current)\s+)?account\b",
            r"\bnew\s+(?:(?:savings|current)\s+)?account\b",
        ]

        return any(
            re.search(pattern, request, re.IGNORECASE)
            for pattern in patterns
        )

    def extract_account_type(self, request):
        savings = re.search(r"\bsavings?\b", request, re.IGNORECASE)
        current = re.search(r"\bcurrent\b", request, re.IGNORECASE)

        if savings and current:
            return None
        if savings:
            return "savings"
        if current:
            return "current"
        return None

    def requires_existing_account(self, request):
        operation_patterns = [
            r"\bdeposit\b",
            r"\bwithdraw(?:al)?\b",
            r"\bbalance\b",
            r"\btransaction(?:s| history| details)?\b",
            r"\bconvert\b",
            r"\bconversion\b",
            r"\bchange account\b",
            r"\bchange my account\b",
            r"\bswitch account\b",
            r"\bswitch my account\b",
            r"\bupgrade account\b",
            r"\bupgrade my account\b",
            r"\bemail\b",
            r"\bsms\b",
            r"\btext message\b",
        ]

        return any(
            re.search(pattern, request, re.IGNORECASE)
            for pattern in operation_patterns
        )

    # ==================================================
    # STATE-AWARE PLAN REPAIR
    # ==================================================

    def repair_plan_for_existing_account(
        self, user_request, plan, account
    ):
        if account is None:
            return plan

        request = user_request.lower().strip()

        if self.is_account_creation_request(request):
            return plan

        def single_step(api, parameters=None):
            return {
                "status": "success",
                "steps": [{
                    "api": api,
                    "parameters": parameters or {}
                }]
            }

        if re.search(
            r"\b(withdraw|withdrawal)\b|take money|take out money|"
            r"cash withdrawal|remove money",
            request
        ):
            amount = self.extract_amount(user_request)
            if amount is not None:
                return single_step(
                    "/account/withdraw",
                    {"amount": amount, "currency": "INR"}
                )

        elif re.search(
            r"\bdeposit\b|put money|add money|add funds",
            request
        ):
            amount = self.extract_amount(user_request)
            if amount is not None:
                return single_step(
                    "/account/deposit",
                    {"amount": amount, "currency": "INR"}
                )

        if any(word in request for word in [
            "transaction", "transactions", "transaction history",
            "account history", "transaction details",
            "show my transactions", "show transactions"
        ]):
            return single_step("/account/transactions")

        if any(word in request for word in [
            "balance", "account balance", "current balance",
            "available balance", "how much money",
            "how much do i have"
        ]):
            return single_step("/account/balance")

        if "email" in request:
            return single_step(
                "/account/notification/email",
                {"notification_type": "confirmation"}
            )

        if any(word in request for word in [
            "sms", "text message", "text me"
        ]):
            return single_step(
                "/account/notification/sms",
                {"notification_type": "confirmation"}
            )

        conversion_keywords = [
            "convert", "conversion", "change account",
            "change my account", "change it to", "change it into",
            "switch account", "switch my account", "switch it to",
            "switch it into", "upgrade account", "upgrade my account",
            "upgrade it to", "upgrade it into"
        ]

        if any(word in request for word in conversion_keywords):
            target_type = self.extract_account_type(request)
            if target_type:
                return single_step(
                    "/account/changeAccountType",
                    {"account_type": target_type}
                )

        return plan

    # ==================================================
    # AMOUNT EXTRACTION
    # ==================================================

    def extract_amount(self, user_request):
        request = user_request.lower().replace(",", "")

        match = re.search(
            r"(?:₹|rs\.?|inr\s*)?\s*(\d+(?:\.\d+)?)\s*(k|thousand)\b",
            request
        )
        if match:
            value = float(match.group(1)) * 1000
            return int(value) if value.is_integer() else value

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

    def detect_ambiguous_request(self, user_request, user_id):
        request = user_request.lower().strip()
        account = self.api_client.get_account(user_id)

        if account is not None:
            return None

        if self.is_account_creation_request(request):
            return None

        ambiguous_phrases = [
            "change to current account", "change into current account",
            "change to current", "change into current",
            "switch to current account", "switch into current account",
            "switch to current", "switch into current",
            "convert to current account", "convert into current account",
            "convert to current", "convert into current",
            "upgrade to current account", "upgrade to current",
            "change to savings account", "change into savings account",
            "change to savings", "change into savings",
            "switch to savings account", "switch to savings",
            "convert to savings account", "convert into savings"
        ]

        if any(phrase in request for phrase in ambiguous_phrases):
            return {
                "status": "clarification_required",
                "message": (
                    "Do you want to create a new account, "
                    "or convert an existing account?"
                )
            }

        return None

    # ==================================================
    # UNSUPPORTED OPERATIONS
    # ==================================================

    def detect_unsupported_operation(self, user_request):
        request = user_request.lower().strip()

        if re.search(
            r"\b(transfer|transfers|send money|send funds)\b",
            request
        ):
            return {
                "status": "failed",
                "message": (
                    "The requested transfer operation is not supported."
                )
            }

        return None

    # ==================================================
    # INTENT VALIDATION
    # ==================================================

    def check_user_intent(self, user_request, plan):
        request = user_request.lower().strip()

        if not isinstance(plan.get("steps"), list) or not plan["steps"]:
            return False, "The generated API plan has no valid steps."

        planned_apis = [
            step.get("api") for step in plan["steps"]
            if isinstance(step, dict)
        ]

        # Account creation must map to the actual catalog endpoint.
        if self.is_account_creation_request(request):
            if planned_apis != ["/account/new"]:
                return False, (
                    "The requested account creation operation "
                    "could not be identified."
                )

        deposit_requested = bool(re.search(
            r"\b(deposit|add funds|add money)\b", request
        ))
        withdrawal_requested = bool(re.search(
            r"\b(withdraw|withdrawal)\b", request
        ))

        if deposit_requested:
            if "/account/deposit" not in planned_apis:
                return False, (
                    "The requested deposit operation could not be identified."
                )
            if "/account/withdraw" in planned_apis:
                return False, "The plan incorrectly includes a withdrawal."

        if withdrawal_requested:
            if "/account/withdraw" not in planned_apis:
                return False, (
                    "The requested withdrawal operation could not be identified."
                )
            if "/account/deposit" in planned_apis:
                return False, "The plan incorrectly includes a deposit."

        if (
            "balance" in request
            and not deposit_requested
            and not withdrawal_requested
        ):
            if "/account/balance" not in planned_apis:
                return False, (
                    "The requested balance operation could not be identified."
                )

        if any(word in request for word in [
            "transaction history", "transactions",
            "transaction details", "account history"
        ]):
            if "/account/transactions" not in planned_apis:
                return False, (
                    "The requested transaction history operation "
                    "could not be identified."
                )

        if any(word in request for word in ["sms", "text message"]):
            if "/account/notification/sms" not in planned_apis:
                return False, (
                    "The requested SMS notification operation "
                    "could not be identified."
                )

        if "email" in request:
            if "/account/notification/email" not in planned_apis:
                return False, (
                    "The requested email notification operation "
                    "could not be identified."
                )

        conversion_requested = any(word in request for word in [
            "convert", "conversion", "change account", "change my account",
            "switch account", "switch my account", "upgrade account",
            "upgrade my account"
        ])

        if conversion_requested:
            if "/account/changeAccountType" not in planned_apis:
                return False, (
                    "The requested account conversion operation "
                    "could not be identified."
                )

        return True, "Intent validation passed."

    # ==================================================
    # USER-FRIENDLY RESPONSE
    # ==================================================

    def create_user_message(self, plan, account, user_id):
        apis = [step["api"] for step in plan["steps"]]

        if "/account/new" in apis and len(apis) == 1:
            if account is None:
                return (
                    "The account operation completed, but account "
                    "details could not be retrieved."
                )

            return (
                f"{account['account_type'].capitalize()} account "
                "created successfully!"
            )

        if "/account/deposit" in apis and len(apis) == 1:
            amount = next(
                step["parameters"]["amount"]
                for step in plan["steps"]
                if step["api"] == "/account/deposit"
            )
            return f"₹{amount} deposited successfully."

        if "/account/withdraw" in apis and len(apis) == 1:
            return (
                f"Withdrawal successful. Remaining balance: "
                f"₹{account['balance']}."
            )

        if "/account/balance" in apis and len(apis) == 1:
            return (
                f"Your current account balance is "
                f"₹{account['balance']}."
            )

        if "/account/changeAccountType" in apis and len(apis) == 1:
            return "Account type changed successfully."

        if "/account/notification/email" in apis and len(apis) == 1:
            return "Confirmation email sent successfully."

        if "/account/notification/sms" in apis and len(apis) == 1:
            return "Confirmation SMS sent successfully."

        if "/account/transactions" in apis and len(apis) == 1:
            transactions = self.api_client.get_transactions(user_id)
            if not transactions:
                return "There are no transactions available yet."
            return (
                f"You have {len(transactions)} transaction(s) "
                "in your account."
            )

        return "Your request was completed successfully."