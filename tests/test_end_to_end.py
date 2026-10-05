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
from app.orchestrator import Orchestrator
from app.api_client import APIClient


def test_real_llm_complete_workflow():

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
    # 3. Create validators and execution components
    # --------------------------------------------------

    validator = APIValidator(catalog_path)
    business_rules = BusinessRules()

    api_client = APIClient()
    orchestrator = Orchestrator(api_client)

    # --------------------------------------------------
    # 4. Natural-language user request
    # --------------------------------------------------

    user_request = """
    I want to open an account.
    This should be a savings account initially.
    After depositing 10000 rupees,
    I want to convert it to a current account.
    Then I should receive an email confirmation.
    """

    # --------------------------------------------------
    # 5. Create prompt for the local LLM
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
    # 6. Generate API plan using REAL local LLM
    # --------------------------------------------------

    response = llm.generate(prompt)

    print("\n" + "=" * 60)
    print("LLM RESPONSE")
    print("=" * 60)
    print(response)

    # --------------------------------------------------
    # 7. Convert LLM response to JSON
    # --------------------------------------------------

    try:
        plan = json.loads(response)

    except json.JSONDecodeError:
        raise AssertionError(
            "Local LLM did not return valid JSON."
        )

    print("\nJSON parsing successful.")

    # --------------------------------------------------
    # 8. API validation
    # --------------------------------------------------

    is_valid, message = validator.validate(plan)

    print("\nAPI VALIDATION")
    print(message)

    assert is_valid, message

    # --------------------------------------------------
    # 9. Get current account state
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

    assert business_valid, business_message

    # --------------------------------------------------
    # 11. Execute API plan
    # --------------------------------------------------

    print("\nAPI EXECUTION")

    results = orchestrator.execute(plan)

    print("\nEXECUTION RESULTS")
    print(json.dumps(results, indent=2))

    # --------------------------------------------------
    # 12. Verify execution succeeded
    # --------------------------------------------------

    assert results["status"] == "success"

    # --------------------------------------------------
    # 13. Verify final account state
    # --------------------------------------------------

    account = api_client.get_account()

    assert account is not None

    assert account["account_type"] == "current"

    assert account["balance"] == 10000

    assert account["currency"] == "INR"

    print("\n" + "=" * 60)
    print("END-TO-END TEST PASSED")
    print("=" * 60)