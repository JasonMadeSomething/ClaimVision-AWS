import json
import os
import sys
import uuid
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import (
    PostgresContainer,  # Optional if using Testcontainers
)

from models import Base, File, Household, User
from models.file import FileStatus

load_dotenv()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))



# -----------------
# ENVIRONMENT MOCKS
# -----------------
@pytest.fixture(autouse=True)
def mock_env():
    """Set required environment variables for testing."""
    os.environ["DATABASE_URL"] = "postgresql://testuser:testpassword@localhost:5432/testdb"
    os.environ["S3_BUCKET_NAME"] = "test-bucket"
    os.environ["COGNITO_USER_POOL_ID"] = "us-east-1_testpool"
    os.environ["COGNITO_USER_POOL_CLIENT_ID"] = "1234567890abcdef1234567890"
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["COGNITO_USER_POOL_CLIENT_SECRET"] = "test-user-pool-client-secret"
    
# -----------------
# DATABASE FIXTURE
# -----------------
@pytest.fixture(scope="function")
def test_db():
    """Provides a fresh test database for each test function."""
    engine = create_engine(os.getenv("DATABASE_URL"))
    TestingSessionLocal = sessionmaker(bind=engine)

    # ✅ Ensure tables are dropped and recreated before each test
    with engine.begin() as conn:
        Base.metadata.drop_all(conn)
        Base.metadata.create_all(conn)

    session = TestingSessionLocal()

    yield session  # ✅ Provide session for the test

    # ✅ Teardown: Drop all tables after each test
    session.rollback()
    session.close()
    with engine.begin() as conn:
        Base.metadata.drop_all(conn)
    engine.dispose()
# -----------------
# API GATEWAY MOCKS
# -----------------
@pytest.fixture
def api_gateway_event():
    """Creates a mock API Gateway event for testing"""

    def _event(http_method="GET", path_params=None, query_params=None, body=None, auth_user="user-123"):
        """Generate an API event, allowing optional auth_user=None for unauthenticated tests"""
        event = {
            "httpMethod": http_method,
            "pathParameters": path_params or {},
            "queryStringParameters": query_params or {},
            "headers": {"Authorization": "Bearer fake-jwt-token"} if auth_user else {},
            "requestContext": {
                "authorizer": {"claims": {"sub": auth_user}} if auth_user else {}
            },
            "body": json.dumps(body) if isinstance(body, dict) else body,
        }
        return event

    return _event

# -----------------
# MOCK S3
# -----------------
@pytest.fixture
def mock_s3():
    """Mock S3 client for testing"""
    with patch("boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        yield mock_s3

# -----------------
# AUTH MOCKS
# -----------------
@pytest.fixture
def auth_event():
    """Mock API Gateway event with an authenticated user."""
    return {
        "requestContext": {
            "authorizer": {"claims": {"sub": "test-user-id"}}
        }
    }

@pytest.fixture(scope="function", autouse=True)
def mock_cognito():
    """✅ Fully mock Cognito interactions for all tests."""
    with patch("boto3.client") as mock_boto_client:
        mock_cognito_client = MagicMock()
        mock_boto_client.return_value = mock_cognito_client

        # ✅ Ensure a **unique** Cognito UserSub is generated per test
        def generate_unique_user_sub(*args, **kwargs):
            return {"UserSub": str(uuid.uuid4())}  # ✅ Unique ID for each test

        mock_cognito_client.sign_up.side_effect = generate_unique_user_sub  # ✅ Apply dynamic user generation

        # ✅ Assign exception classes directly, instead of using a nested class
        mock_cognito_client.exceptions = MagicMock()
        mock_cognito_client.exceptions.UsernameExistsException = type("UsernameExistsException", (Exception,), {})
        mock_cognito_client.exceptions.InvalidPasswordException = type("InvalidPasswordException", (Exception,), {})
        mock_cognito_client.exceptions.UserNotFoundException = type("UserNotFoundException", (Exception,), {})
        mock_cognito_client.exceptions.NotAuthorizedException = type("NotAuthorizedException", (Exception,), {})
        mock_cognito_client.exceptions.InternalErrorException = type("InternalErrorException", (Exception,), {})
        mock_cognito_client.exceptions.TooManyRequestsException = type("TooManyRequestsException", (Exception,), {})
        mock_cognito_client.exceptions.UserNotConfirmedException = type("UserNotConfirmedException", (Exception,), {})
        mock_cognito_client.exceptions.PasswordResetRequiredException = type("PasswordResetRequiredException", (Exception,), {})
        mock_cognito_client.exceptions.CodeMismatchException = type("CodeMismatchException", (Exception,), {})  # ✅ Assign properly
        mock_cognito_client.exceptions.LimitExceededException = type("LimitExceededException", (Exception,), {})  # ✅ Assign properly

        # ✅ Mock Attribute Updates (e.g., Household ID)
        mock_cognito_client.admin_update_user_attributes.return_value = {}

        # ✅ Mock Cognito Login
        mock_cognito_client.initiate_auth.return_value = {
            "AuthenticationResult": {
                "AccessToken": "mock-access-token",
                "IdToken": "mock-id-token",
                "RefreshToken": "mock-refresh-token"
            }
        }

        yield mock_cognito_client  # ✅ Provide mock to all tests

        mock_cognito_client.reset_mock()

@pytest.fixture
def seed_file(test_db):
    """Inserts a test file into the database."""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()
    file_id = uuid.uuid4()

    test_household = Household(id=household_id, name="Test Household")
    test_user = User(
        id=user_id,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        household_id=household_id
    )
    test_file = File(
        id=file_id,
        uploaded_by=user_id,
        household_id=household_id,
        file_name="original.jpg",
        s3_key="original-key",
        status="UPLOADED",
        file_metadata={"mime_type": "image/jpeg", "size": 12345},
    )

    test_db.add_all([test_household, test_user, test_file])
    test_db.commit()

    return file_id, user_id, household_id

@pytest.fixture
def seed_files(test_db):
    """Insert multiple test files into the database."""
    household_id = uuid.uuid4()
    user_id = uuid.uuid4()

    test_household = Household(id=household_id, name="Test Household")
    test_user = User(
        id=user_id,
        email="test@example.com",
        first_name="Test",
        last_name="User",
        household_id=household_id,
    )

    test_files = [
        File(
            id=uuid.uuid4(),
            uploaded_by=user_id,
            household_id=household_id,
            file_name=f"file_{i}.jpg",
            s3_key=f"key_{i}",
            status=FileStatus.UPLOADED,
            labels=[],
            file_metadata={"mime_type": "image/jpeg", "size": 1234 + i},
        )
        for i in range(5)
    ]

    test_db.add_all([test_household, test_user, *test_files])
    test_db.commit()

    return user_id, household_id, test_files