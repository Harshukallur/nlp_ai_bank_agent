import os
import sys

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

sys.path.insert(0, PROJECT_ROOT)

from app.service import AccountService


def test_real_llm_rejects_unsupported_transfer():

    # --------------------------------------------------
    # 1. Create the actual AccountService
    # --------------------------------------------------

    service = AccountService()

    # --------------------------------------------------
    # 2. User requests an unsupported transfer operation
    # --------------------------------------------------

    user_request = (
        "I want to transfer 20000 rupees "
        "to another bank account."
    )

    # --------------------------------------------------
    # 3. Process request through the REAL application
    # --------------------------------------------------

    result = service.process_request(user_request)

    # --------------------------------------------------
    # 4. Print result for debugging
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print("END-TO-END RESULT")
    print("=" * 60)
    print(result)

    # --------------------------------------------------
    # 5. Verify request was rejected
    # --------------------------------------------------

    assert result["status"] == "failed", (
        "Unsupported transfer request should be rejected."
    )

    # --------------------------------------------------
    # 6. Verify the correct rejection message
    # --------------------------------------------------

    assert "transfer" in result["message"].lower(), (
        "Rejection message should mention the unsupported "
        "transfer operation."
    )

    # --------------------------------------------------
    # 7. Verify no API was executed
    # --------------------------------------------------

    account = service.api_client.get_account()

    assert account is None, (
        "No account should be created because the "
        "unsupported transfer request must be rejected "
        "before API execution."
    )

    # --------------------------------------------------
    # 8. Verify no activity was recorded
    # --------------------------------------------------

    activity = service.api_client.get_activity()

    assert activity == [], (
        "No account activity should be recorded for a "
        "rejected transfer request."
    )

    print("\n" + "=" * 60)
    print("NEGATIVE END-TO-END TEST PASSED")
    print("=" * 60)