from app.service import AccountService
from app.api_client import APIClient


def create_test_service():

    service = AccountService.__new__(AccountService)

    service.api_client = APIClient()

    return service


def test_ambiguous_change_without_account():

    service = create_test_service()

    result = service.detect_ambiguous_request(
        "change to current account"
    )

    assert result is not None
    assert result["status"] == "clarification_required"


def test_ambiguous_convert_without_account():

    service = create_test_service()

    result = service.detect_ambiguous_request(
        "convert into current account"
    )

    assert result is not None
    assert result["status"] == "clarification_required"


def test_creation_and_conversion_is_not_ambiguous():

    service = create_test_service()

    result = service.detect_ambiguous_request(
        "create a savings account and convert it to current"
    )

    assert result is None


def test_explicit_existing_account_is_not_ambiguous():

    service = create_test_service()

    result = service.detect_ambiguous_request(
        "change the existing account into current account"
    )

    assert result is None