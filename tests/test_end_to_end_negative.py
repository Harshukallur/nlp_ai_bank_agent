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


def test_real_llm_rejects_unsupported_transfer():

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

    validator = APIValidator(catalog_path)

    # --------------------------------------------------
    # 3. User asks for an unsupported operation
    # --------------------------------------------------

    user_request = """
    I want to transfer 20000 rupees to another bank account.
    """

    # --------------------------------------------------
    # 4. Create prompt
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
3. Do not substitute one API for another.
4. If the requested operation does not have a matching API
   in the catalog, do not use a different API.
5. Do not use /account/deposit for a transfer request.
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

If the requested operation cannot be performed using
the available APIs, return:

{{
    "status": "failed",
    "steps": []
}}
"""

    # --------------------------------------------------
    # 5. Generate plan using REAL local LLM
    # --------------------------------------------------

    response = llm.generate(prompt)

    print("\n" + "=" * 60)
    print("LLM RESPONSE")
    print("=" * 60)
    print(response)

    # --------------------------------------------------
    # 6. Parse JSON
    # --------------------------------------------------

    try:
        plan = json.loads(response)

    except json.JSONDecodeError:
        raise AssertionError(
            "Local LLM did not return valid JSON."
        )

    # --------------------------------------------------
    # 7. Verify that LLM did NOT generate deposit API
    # --------------------------------------------------

    planned_apis = [
        step.get("api")
        for step in plan.get("steps", [])
    ]

    assert "/account/deposit" not in planned_apis

    # --------------------------------------------------
    # 8. Verify the request was rejected
    # --------------------------------------------------

    assert plan.get("status") == "failed"

    # --------------------------------------------------
    # 9. Verify no API steps were generated
    # --------------------------------------------------

    assert plan.get("steps") == []

    print("\n" + "=" * 60)
    print("NEGATIVE END-TO-END TEST PASSED")
    print("=" * 60)