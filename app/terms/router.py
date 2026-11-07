from fastapi import APIRouter
from app.terms.application.query import terms_query_service
from app.terms.schemas import TermsResponse

router = APIRouter(prefix="/terms", tags=["terms"])


# deliberately public (no AuthDep): the terms are public anyway, and the app
# needs them during onboarding, before a profile (or even a login) exists
@router.get("/current")
def get_current_terms() -> TermsResponse:
    terms = terms_query_service.get_current_terms()
    return TermsResponse.model_validate(terms, from_attributes=True)
