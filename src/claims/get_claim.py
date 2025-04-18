"""
Lambda handler for retrieving a claim and its associated data.

This module handles the retrieval of claim details from the ClaimVision system,
ensuring proper authorization and data access.
"""
from utils.logging_utils import get_logger
from sqlalchemy.exc import IntegrityError, OperationalError
from utils import response
from utils.lambda_utils import standard_lambda_handler, extract_uuid_param
from models import Claim


logger = get_logger(__name__)

@standard_lambda_handler(requires_auth=True)
def lambda_handler(event: dict, _context=None, db_session=None, user=None) -> dict:
    """
    Handles retrieving a claim by ID for the authenticated user's household.

    Args:
        event (dict): API Gateway event containing authentication details and claim ID.
        _context (dict): Lambda execution context (unused).
        db_session (Session, optional): SQLAlchemy session for testing. Defaults to None.
        user (User): Authenticated user object (provided by decorator).

    Returns:
        dict: API response containing the claim details or an error message.
    """
    # Extract claim ID from path parameters
    success, result = extract_uuid_param(event, "claim_id")
    if not success:
        return result  # Return error response
    
    claim_id = result
    
    try:
        # Query the claim
        claim = db_session.query(Claim).filter_by(id=claim_id).first()
        
        # Check if claim exists
        if not claim:
            return response.api_response(404, error_details="Claim not found")
        
        # Check if claim is soft-deleted
        if claim.deleted:
            return response.api_response(404, error_details="Claim not found")
        
        # Check if user has access to the claim (belongs to their household)
        if str(claim.household_id) != str(user.household_id):
            # Return 404 for security reasons (don't reveal that the claim exists)
            return response.api_response(404, error_details="Claim not found")
        
        # Convert claim to dictionary for response
        claim_data = {
            "id": str(claim.id),
            "household_id": str(claim.household_id),
            "title": claim.title,
            "description": claim.description or "",
            "date_of_loss": claim.date_of_loss.strftime("%Y-%m-%d") if claim.date_of_loss else None
        }
        
        # Add created_at and updated_at if they exist
        if hasattr(claim, 'created_at') and claim.created_at:
            claim_data["created_at"] = claim.created_at.isoformat()
        
        if hasattr(claim, 'updated_at') and claim.updated_at:
            claim_data["updated_at"] = claim.updated_at.isoformat()
        
        return response.api_response(200, data=claim_data)
        
    except IntegrityError as e:
        logger.error("Database integrity error when retrieving claim %s: %s", str(claim_id), str(e))
        return response.api_response(500, error_details="Database integrity error when retrieving claim")
    except OperationalError as e:
        logger.error("Database operational error when retrieving claim %s: %s", str(claim_id), str(e))
        return response.api_response(500, error_details="Database operational error when retrieving claim")
    except Exception as e:
        logger.error("Error retrieving claim: %s", str(e))
        return response.api_response(500, error_details="Internal server error")
