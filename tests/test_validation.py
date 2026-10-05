import json
import os
import sys

import pytest

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

sys.path.insert(0, PROJECT_ROOT)

from app.validator import APIValidator
from app.business_rules import BusinessRules


@pytest.fixture
def test_data():
    test_file = os.path.join(
        os.path.dirname(__file__),
        "test_cases.json"
    )

    with open(test_file, "r") as file:
        return json.load(file)


@pytest.fixture
def validator():
    catalog_path = os.path.join(
        PROJECT_ROOT,
        "config",
        "api_catalog.json"
    )

    return APIValidator(catalog_path)


@pytest.fixture
def business_rules():
    return BusinessRules()


@pytest.mark.parametrize(
    "test_index",
    range(12)
)
def test_api_validation(
    test_index,
    test_data,
    validator
):
    test_case = test_data["test_cases"][test_index]

    plan = test_case["plan"]

    is_valid, message = validator.validate(plan)

    expected = test_case["expected_api_validation"]

    assert is_valid == expected, (
        f"\nTest: {test_case['name']}"
        f"\nExpected API validation: {expected}"
        f"\nActual: {is_valid}"
        f"\nMessage: {message}"
    )


@pytest.mark.parametrize(
    "test_index",
    range(12)
)
def test_business_rules(
    test_index,
    test_data,
    business_rules
):
    test_case = test_data["test_cases"][test_index]

    plan = test_case["plan"]

    account_state = test_case.get(
        "account_state",
        {
            "account_exists": False,
            "account_type": None,
            "balance": 0
        }
    )

    is_valid, message = business_rules.validate(
        plan,
        account_state
    )

    expected = test_case["expected_business_validation"]

    assert is_valid == expected, (
        f"\nTest: {test_case['name']}"
        f"\nExpected business validation: {expected}"
        f"\nActual: {is_valid}"
        f"\nMessage: {message}"
    )