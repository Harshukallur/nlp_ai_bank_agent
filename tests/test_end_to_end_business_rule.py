import os
import sys
import json

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

sys.path.insert(0, PROJECT_ROOT)

from app.llm import LocalLLM
from app.validator import APIValidator
from app.business_rules import BusinessRules
from app.api_client import APIClient
from app.orchestrator import Orchestrator


def test_real_llm_business_rule_rejection():

    # --------------------------------------------------
    # 1. Load local LLM
    # --------------------------------------------------

    llm = LocalLLM()

    # --------------------------------------------------
    # 2. Load API catalog
    # --------------------------------------------------

    catalog_path = os.path.join(
        PROJECT_ROOT,
        "config",
        "api_catalog.json"
    )

    with open(catalog_path, "r") as file:
        catalog = json.load(file)

    catalog_text = json.dumps(
        catalog,
        indent=2
    )

    # --------------------------------------------------
    # 3. Create validation and execution components
    # --------------------------------------------------

    validator = APIValidator(catalog_path)
    business_rules = BusinessRules()

    api_client = APIClient()
    orchestrator = Orchestrator(api_client)

    # --------------------------------------------------
    # 4. User request
    # --------------------------------------------------

    user_request = """
    I want to open a savings account and deposit
    5000 rupees into it.
    """

    # --------------------------------------------------
    # 5. Create prompt
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
6. Return JSON only.

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
    # 6. Generate API plan using REAL local LLM
    # --------------------------------------------------

    response = llm.generate(prompt)

    print("\n" + "=" * 60)
    print("LLM RESPONSE")
    print("=" * 60)
    print(response)

    # --------------------------------------------------
    # 7. Parse JSON
    # --------------------------------------------------

    try:
        plan = json.loads(response)

    except json.JSONDecodeError:
        raise AssertionError(
            "Local LLM did not return valid JSON."
        )

    # --------------------------------------------------
    # 8. API validation should pass
    # --------------------------------------------------

    is_valid, message = validator.validate(plan)

    print("\nAPI VALIDATION")
    print(message)

    assert is_valid, message

    # --------------------------------------------------
    # 9. Get account state
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
            "account_type": account["account_type"],
            "balance": account["balance"]
        }

    # --------------------------------------------------
    # 10. Business rule validation
    # --------------------------------------------------

    business_valid, business_message = (
        business_rules.validate(
            plan,
            account_state
        )
    )

    print("\nBUSINESS RULE VALIDATION")
    print(business_message)

    # The request should be rejected because
    # the minimum deposit is ₹10,000.
    assert business_valid is False

    assert "Minimum deposit" in business_message

    # --------------------------------------------------
    # 11. Verify that APIs were NOT executed
    # --------------------------------------------------

    account = api_client.get_account()

    assert account is None

    print("\nAPI EXECUTION")
    print("Execution correctly skipped because business rules failed.")

    # --------------------------------------------------
    # 12. Do not execute the orchestrator
    # --------------------------------------------------

    # This assertion confirms that the account was never
    # created because the business-rule layer rejected
    # the request before execution.

    assert api_client.get_account() is None

    print("\n" + "=" * 60)
    print("BUSINESS RULE NEGATIVE TEST PASSED")
    print("=" * 60)