import os
import sys

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

sys.path.insert(0, PROJECT_ROOT)

from app.api_client import APIClient
from app.orchestrator import Orchestrator


def test_create_account():
    api_client = APIClient()
    orchestrator = Orchestrator(api_client)

    plan = {
        "status": "success",
        "steps": [
            {
                "api": "/account/new",
                "parameters": {
                    "account_type": "savings"
                }
            }
        ]
    }

    results = orchestrator.execute(plan)

    assert results["status"] == "success"
    assert results["results"][0]["result"]["status"] == "success"

    account = api_client.get_account()

    assert account is not None
    assert account["account_type"] == "savings"
    assert account["balance"] == 0


def test_deposit_updates_balance():
    api_client = APIClient()
    orchestrator = Orchestrator(api_client)

    create_plan = {
        "status": "success",
        "steps": [
            {
                "api": "/account/new",
                "parameters": {
                    "account_type": "savings"
                }
            }
        ]
    }

    orchestrator.execute(create_plan)

    deposit_plan = {
        "status": "success",
        "steps": [
            {
                "api": "/account/deposit",
                "parameters": {
                    "amount": 10000,
                    "currency": "INR"
                }
            }
        ]
    }

    results = orchestrator.execute(deposit_plan)

    assert results["status"] == "success"
    assert results["results"][0]["result"]["status"] == "success"

    account = api_client.get_account()

    assert account["balance"] == 10000


def test_change_account_type():
    api_client = APIClient()
    orchestrator = Orchestrator(api_client)

    create_plan = {
        "status": "success",
        "steps": [
            {
                "api": "/account/new",
                "parameters": {
                    "account_type": "savings"
                }
            }
        ]
    }

    orchestrator.execute(create_plan)

    deposit_plan = {
        "status": "success",
        "steps": [
            {
                "api": "/account/deposit",
                "parameters": {
                    "amount": 10000,
                    "currency": "INR"
                }
            }
        ]
    }

    orchestrator.execute(deposit_plan)

    change_plan = {
        "status": "success",
        "steps": [
            {
                "api": "/account/changeAccountType",
                "parameters": {
                    "account_type": "current"
                }
            }
        ]
    }

    results = orchestrator.execute(change_plan)

    assert results["status"] == "success"
    assert results["results"][0]["result"]["status"] == "success"

    account = api_client.get_account()

    assert account["account_type"] == "current"
    assert account["balance"] == 10000


def test_email_confirmation():
    api_client = APIClient()
    orchestrator = Orchestrator(api_client)

    create_plan = {
        "status": "success",
        "steps": [
            {
                "api": "/account/new",
                "parameters": {
                    "account_type": "savings"
                }
            }
        ]
    }

    orchestrator.execute(create_plan)

    email_plan = {
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

    results = orchestrator.execute(email_plan)

    assert results["status"] == "success"
    assert results["results"][0]["result"]["status"] == "success"
    assert (
        results["results"][0]["result"]["message"]
        == "Email confirmation sent."
    )


def test_complete_workflow():
    api_client = APIClient()
    orchestrator = Orchestrator(api_client)

    plan = {
        "status": "success",
        "steps": [
            {
                "api": "/account/new",
                "parameters": {
                    "account_type": "savings"
                }
            },
            {
                "api": "/account/deposit",
                "parameters": {
                    "amount": 10000,
                    "currency": "INR"
                }
            },
            {
                "api": "/account/changeAccountType",
                "parameters": {
                    "account_type": "current"
                }
            },
            {
                "api": "/account/notification/email",
                "parameters": {
                    "notification_type": "confirmation"
                }
            }
        ]
    }

    results = orchestrator.execute(plan)

    # Overall execution should succeed
    assert results["status"] == "success"

    # Four APIs should have executed
    assert len(results["results"]) == 4

    # Every API should succeed
    for result in results["results"]:
        assert result["result"]["status"] == "success"

    # Check final account state
    account = api_client.get_account()

    assert account is not None
    assert account["account_type"] == "current"
    assert account["balance"] == 10000
    assert account["currency"] == "INR"
def test_execution_stops_when_api_fails():
    class FailingAPIClient:
        def __init__(self):
            self.calls = []

        def call(self, endpoint, parameters):
            self.calls.append(endpoint)

            # Simulate failure at the deposit API
            if endpoint == "/account/deposit":
                return {
                    "status": "failed",
                    "message": "Simulated API failure."
                }

            return {
                "status": "success"
            }

    api_client = FailingAPIClient()
    orchestrator = Orchestrator(api_client)

    plan = {
        "status": "success",
        "steps": [
            {
                "api": "/account/new",
                "parameters": {
                    "account_type": "savings"
                }
            },
            {
                "api": "/account/deposit",
                "parameters": {
                    "amount": 10000,
                    "currency": "INR"
                }
            },
            {
                "api": "/account/notification/email",
                "parameters": {
                    "notification_type": "confirmation"
                }
            }
        ]
    }

    results = orchestrator.execute(plan)

    # Overall execution should fail
    assert results["status"] == "failed"

    # Failure should occur at step 2
    assert results["failed_step"] == 2

    # Only the first two APIs should have been called
    assert api_client.calls == [
        "/account/new",
        "/account/deposit"
    ]

    # Email API must NOT execute after deposit failure
    assert "/account/notification/email" not in api_client.calls

    # Two results should be recorded
    assert len(results["results"]) == 2

    # First API succeeded
    assert results["results"][0]["result"]["status"] == "success"

    # Second API failed
    assert results["results"][1]["result"]["status"] == "failed"