import json

from app.llm import LocalLLM
from app.validator import APIValidator
from app.business_rules import BusinessRules
from app.orchestrator import Orchestrator
from app.api_client import APIClient

# --------------------------------------------------
# Intent Validation
# --------------------------------------------------

def check_user_intent(user_request, plan):

    request = user_request.lower().strip()

    # --------------------------------------------------
    # Transfer keywords
    # --------------------------------------------------

    transfer_keywords = [
        "transfer",
        "send money",
        "send funds",
        "bank transfer",
        "transfer money"
    ]

    # --------------------------------------------------
    # Deposit keywords
    # --------------------------------------------------

    deposit_keywords = [
        "deposit",
        "deposit money",
        "put money",
        "add money",
        "add funds"
    ]

    planned_apis = [
        step.get("api")
        for step in plan.get("steps", [])
    ]

    # --------------------------------------------------
    # Check TRANSFER intent
    # --------------------------------------------------

    if any(
        keyword in request
        for keyword in transfer_keywords
    ):

        if "/account/deposit" in planned_apis:

            return (
                False,
                "User requested a transfer, "
                "but the LLM generated a deposit API."
            )

    # --------------------------------------------------
    # Check DEPOSIT intent
    # --------------------------------------------------

    if any(
        keyword in request
        for keyword in deposit_keywords
    ):

        if "/account/deposit" not in planned_apis:

            return (
                False,
                "User requested a deposit, "
                "but the LLM did not generate "
                "the deposit API."
            )

    return True, "Intent validation passed."


# --------------------------------------------------
# Display Account Status
# --------------------------------------------------

def show_account_status(api_client):

    account = api_client.get_account()

    print("\n" + "=" * 60)

    print("ACCOUNT STATUS")

    print("=" * 60)

    if account is None:

        print("No account has been created yet.")

    else:

        print(
            f"Account ID:     {account['account_id']}"
        )

        print(
            f"Account Type:   {account['account_type']}"
        )

        print(
            f"Balance:        ₹{account['balance']}"
        )

        print(
            f"Currency:       {account['currency']}"
        )

    print("=" * 60 + "\n")


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    # --------------------------------------------------
    # 1. Load local LLM ONCE
    # --------------------------------------------------

    print("\nLoading local LLM...")

    llm = LocalLLM()

    print("\nModel is ready.")

    print(
        "Commands: type 'status' to view account "
        "or 'exit' to stop.\n"
    )

    # --------------------------------------------------
    # 2. Load API catalog
    # --------------------------------------------------

    catalog_path = "config/api_catalog.json"

    with open(catalog_path, "r") as file:

        catalog = json.load(file)

    catalog_text = json.dumps(
        catalog,
        indent=2
    )

    # --------------------------------------------------
    # 3. Create API validator
    # --------------------------------------------------

    validator = APIValidator(
        catalog_path
    )

    # --------------------------------------------------
    # 4. Create Business Rules
    # --------------------------------------------------

    business_rules = BusinessRules()

    # --------------------------------------------------
    # 5. Create API Client
    # --------------------------------------------------

    api_client = APIClient()

    # --------------------------------------------------
    # 6. Create Orchestrator
    # --------------------------------------------------

    orchestrator = Orchestrator(
        api_client
    )

    # --------------------------------------------------
    # 7. Interactive loop
    # --------------------------------------------------

    while True:

        user_request = input(
            "Enter your request: "
        )

        command = user_request.lower().strip()

        # --------------------------------------------------
        # EXIT
        # --------------------------------------------------

        if command == "exit":

            print("Exiting...")

            break

        # --------------------------------------------------
        # STATUS
        # --------------------------------------------------

        if command == "status":

            show_account_status(
                api_client
            )

            continue

        # --------------------------------------------------
        # Create LLM prompt
        # --------------------------------------------------

        prompt = f"""
USER REQUEST:

{user_request}

API CATALOG:

{catalog_text}

Generate an API execution plan.

Rules:

1. Only use APIs from the catalog.
2. Do not invent APIs.
3. Extract parameters from the user request.
4. Preserve the required execution order.
5. Do not reinterpret the user's request.
6. If the requested operation does not have a matching API
   in the catalog, do not substitute another API.
7. Return JSON only.

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

        # --------------------------------------------------
        # Generate API plan
        # --------------------------------------------------

        response = llm.generate(
            prompt
        )

        print("\nLLM RESPONSE:")

        print(response)

        # --------------------------------------------------
        # Parse JSON
        # --------------------------------------------------

        try:

            plan = json.loads(
                response
            )

        except json.JSONDecodeError:

            print("\nJSON VALIDATION:")

            print(
                "FAILED - LLM response is "
                "not valid JSON."
            )

            print("Request rejected.")

            print(
                "\n" + "-" * 60 + "\n"
            )

            continue

        print("\nJSON VALIDATION:")

        print(
            "PASSED - Valid JSON received."
        )

        # --------------------------------------------------
        # API validation
        # --------------------------------------------------

        is_valid, message = validator.validate(
            plan
        )

        print("\nAPI VALIDATION:")

        print(message)

        if not is_valid:

            print("Request rejected.")

            print(
                "\n" + "-" * 60 + "\n"
            )

            continue

        print("API plan is valid.")

        # --------------------------------------------------
        # Intent validation
        # --------------------------------------------------

        intent_valid, intent_message = (
            check_user_intent(
                user_request,
                plan
            )
        )

        print("\nINTENT VALIDATION:")

        print(intent_message)

        if not intent_valid:

            print("Request rejected.")

            print(
                "\n" + "-" * 60 + "\n"
            )

            continue

        print(
            "User intent matches API plan."
        )

        # --------------------------------------------------
        # Build current account state
        # --------------------------------------------------

        account = api_client.get_account()

        if account is None:

            account_state = {
                "account_exists": False,
                "account_type": None,
                "balance": 0
            }

        else:

            account_state = {
                "account_exists": True,
                "account_type": account[
                    "account_type"
                ],
                "balance": account[
                    "balance"
                ]
            }

        # --------------------------------------------------
        # Business rule validation
        # --------------------------------------------------

        business_valid, business_message = (
            business_rules.validate(
                plan,
                account_state
            )
        )

        print(
            "\nBUSINESS RULE VALIDATION:"
        )

        print(business_message)

        if not business_valid:

            print("Request rejected.")

            print(
                "\n" + "-" * 60 + "\n"
            )

            continue

        print(
            "Business rules passed."
        )

        # --------------------------------------------------
        # API execution
        # --------------------------------------------------

        print("\nAPI EXECUTION:")

        results = orchestrator.execute(
            plan
        )

        # --------------------------------------------------
        # Display execution results
        # --------------------------------------------------

        print("\nEXECUTION RESULTS:")

        print(
            json.dumps(
                results,
                indent=2
            )
        )

        # --------------------------------------------------
        # Display updated account
        # --------------------------------------------------

        account = api_client.get_account()

        if account is not None:

            print(
                "\nUPDATED ACCOUNT:"
            )

            print(
                f"Account ID:   "
                f"{account['account_id']}"
            )

            print(
                f"Type:         "
                f"{account['account_type']}"
            )

            print(
                f"Balance:      "
                f"₹{account['balance']}"
            )

            print(
                f"Currency:     "
                f"{account['currency']}"
            )

        print(
            "\n" + "=" * 60 + "\n"
        )


# --------------------------------------------------
# Application entry point
# --------------------------------------------------

if __name__ == "__main__":

    main()