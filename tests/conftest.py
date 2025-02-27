import os
import sys
import json
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock
from testcontainers.postgres import PostgresContainer  # Optional if using Testcontainers
from models import File, Base 
from dotenv import load_dotenv

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

        # ✅ Mock Cognito exceptions
        class CognitoExceptions:
            class UsernameExistsException(Exception):
                pass

            class InvalidPasswordException(Exception):
                pass

            class UserNotFoundException(Exception):
                pass

            class NotAuthorizedException(Exception):
                pass

            class InternalErrorException(Exception):
                pass

        mock_cognito_client.exceptions = CognitoExceptions  # ✅ Assign exceptions

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
