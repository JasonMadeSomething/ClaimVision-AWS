import json
import uuid
import pytest
from unittest.mock import patch
from claims.delete_claim import lambda_handler
from models.claim import Claim
from models.household import Household
from models.user import User
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

def test_delete_claim_success(test_db, api_gateway_event):
    """ Test successful claim deletion"""
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()

    # Create household, user, and claim
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=uuid.uuid4(), email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim", date_of_loss=datetime(2024, 1, 10))
    
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()

    event = api_gateway_event(http_method="DELETE", path_params={"claim_id": str(claim_id)}, auth_user=str(test_user.id))
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert "Claim deleted successfully" in body["message"]

def test_delete_claim_unauthorized(test_db, api_gateway_event):
    """ Test deleting a claim that belongs to another user"""

    # Create two separate households
    authorized_household_id = uuid.uuid4()
    unauthorized_household_id = uuid.uuid4()

    test_household = Household(id=authorized_household_id, name="Authorized Household")
    unauthorized_household = Household(id=unauthorized_household_id, name="Unauthorized Household")
    
    test_db.add_all([test_household, unauthorized_household])
    test_db.commit()

    # Create two users, each in their own household
    authorized_user_id = uuid.uuid4()
    unauthorized_user_id = uuid.uuid4()

    authorized_user = User(id=authorized_user_id, email="auth@example.com", first_name="Auth", last_name="User", household_id=authorized_household_id)
    unauthorized_user = User(id=unauthorized_user_id, email="unauth@example.com", first_name="Unauth", last_name="User", household_id=unauthorized_household_id)

    test_db.add_all([authorized_user, unauthorized_user])
    test_db.commit()

    # Now create a claim in the authorized household
    claim_id = uuid.uuid4()
    test_claim = Claim(id=claim_id, household_id=authorized_household_id, title="Test Claim", date_of_loss=datetime(2024, 1, 10))

    test_db.add(test_claim)
    test_db.commit()

    # The unauthorized user tries to delete the claim
    event = api_gateway_event(http_method="DELETE", path_params={"claim_id": str(claim_id)}, auth_user=str(unauthorized_user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 404  # Security: Pretend it doesn't exist


def test_delete_claim_not_found(test_db, api_gateway_event):
    """ Test deleting a non-existent claim"""

    household_id = uuid.uuid4()
    user_id = uuid.uuid4()  # Generate a valid user UUID

    # Create a household and user before calling lambda_handler
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_db.add_all([test_household, test_user])
    test_db.commit()

    # Attempt to delete a claim that doesn’t exist
    event = api_gateway_event(http_method="DELETE", path_params={"claim_id": str(uuid.uuid4())}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])

    assert response["statusCode"] == 404
    assert "Claim not found" in body["error_details"]


@pytest.fixture
def seed_test_user(test_db):
    """Creates a household and a user for testing."""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()

    test_household = Household(id=household_id, name="Test Household")
    test_user = User(
        id=user_id,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        household_id=household_id
    )

    test_db.add_all([test_household, test_user])
    test_db.commit()

    return household_id, user_id

def test_delete_claim_invalid_id(api_gateway_event, seed_test_user, test_db):
    """ Test deleting a claim with an invalid UUID"""
    # Get the user ID from the fixture
    household_id, user_id = seed_test_user
    
    # Use a completely invalid format for claim_id that will trigger the 400 error
    event = api_gateway_event(http_method="DELETE", path_params={"claim_id": "abc"}, auth_user=str(user_id))
    
    # Call the lambda handler directly with the invalid UUID
    response_obj = lambda_handler(event, {})
    body = json.loads(response_obj["body"])
    
    # The extract_uuid_param function should return a 400 status code for invalid UUIDs
    assert response_obj["statusCode"] == 400
    assert "Invalid claim_id format" in body["error_details"]


def test_delete_claim_db_failure(api_gateway_event):
    """ Test handling a database failure during claim deletion"""
    # Create a valid UUID for the test
    valid_uuid = str(uuid.uuid4())
    
    # We need to patch the database session after it's been created by the decorator
    with patch("utils.lambda_utils.get_db_session") as mock_db:
        # Configure the mock to raise an exception when used
        mock_session = mock_db.return_value
        mock_session.query.side_effect = SQLAlchemyError("Database error occurred")
        
        # Call the lambda handler with a valid UUID
        event = api_gateway_event(
            http_method="DELETE", 
            path_params={"claim_id": valid_uuid}, 
            auth_user=str(uuid.uuid4())
        )
        response = lambda_handler(event, {})
        body = json.loads(response["body"])
    
    assert response["statusCode"] == 500
    assert "Database error" in body["error_details"]