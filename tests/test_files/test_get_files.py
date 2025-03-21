"""Test retrieving files for a user"""
import json
import uuid
import pytest
from unittest.mock import patch
from files.get_files import lambda_handler
from models import User, Household


@pytest.mark.usefixtures("seed_files")
def test_get_files_success(api_gateway_event, test_db, seed_files):
    """Test retrieving files successfully."""
    user_id, _, _ = seed_files

    event = api_gateway_event(
        http_method="GET",
        query_params={"limit": "10"},
        auth_user=str(user_id),
    )

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert "message" in body
    assert body["message"] == "OK"
    assert len(body["data"]["files"]) == 5


def test_get_files_pagination(api_gateway_event, test_db, seed_files, mock_s3):
    """Test retrieving files with pagination."""
    user_id, _, _ = seed_files

    mock_s3.generate_presigned_url.return_value = "https://signed-url.com/file"

    event = api_gateway_event(
        http_method="GET",
        query_params={"limit": "2", "offset": "0"},
        auth_user=str(user_id),
    )

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert "message" in body
    assert len(body["data"]["files"]) == 2


def test_get_files_empty(api_gateway_event, test_db):
    """Test retrieving files when none exist."""
    user_id = uuid.uuid4()
    household_id = uuid.uuid4()

    test_household = Household(id=household_id, name="Empty Household")
    test_user = User(
        id=user_id,
        email="empty@example.com",
        first_name="Empty",
        last_name="User",
        household_id=household_id,
    )

    test_db.add_all([test_household, test_user])
    test_db.commit()

    event = api_gateway_event(
        http_method="GET",
        query_params={"limit": "10"},
        auth_user=str(user_id),
    )

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert "message" in body
    assert len(body["data"]["files"]) == 0


def test_get_files_invalid_limit(api_gateway_event, test_db, seed_files):
    """Test retrieving files with an invalid limit parameter (should return 400 Bad Request)"""
    user_id, _, _ = seed_files

    event = api_gateway_event(
        http_method="GET",
        query_params={"limit": "invalid"},
        auth_user=str(user_id),
    )

    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 400
    assert "error_details" in body
    assert body["error_details"] == "Invalid pagination parameters"

def test_get_files_s3_failure(api_gateway_event, test_db, mock_s3, seed_files):
    """❌ Test failure when S3 fails to generate signed URLs."""
    user_id, household_id, _ = seed_files  # Unpack the tuple correctly
    
    # ✅ Mock S3 failure - need to patch the right method
    mock_s3.generate_presigned_url.return_value = None
    
    event = api_gateway_event(http_method="GET", auth_user=str(user_id))
    
    # Use patch to directly target the function in get_files.py
    with patch("files.get_files.generate_presigned_url", return_value=None):
        response = lambda_handler(event, {}, db_session=test_db)
        body = json.loads(response["body"])
    
        assert response["statusCode"] == 200  # ✅ Still returns a 200
        assert "files" in body["data"]
        assert len(body["data"]["files"]) >= 0
        assert all(file["signed_url"] is None for file in body["data"]["files"])