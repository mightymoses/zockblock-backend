import structlog
from app.config import get_settings
from app.terms.exceptions import TermsNotConfiguredException
from app.terms.models import CurrentTerms

logger = structlog.get_logger()


def get_current_terms() -> CurrentTerms:
    """Single source of truth for the current terms - also used by users to
    validate acceptances. Fails loudly instead of handing out an empty version
    the app would then send back as "accepted"."""
    settings = get_settings()
    if not settings.current_terms_version or not settings.current_terms_url:
        logger.error(
            "terms not configured",
            has_version=bool(settings.current_terms_version),
            has_url=bool(settings.current_terms_url),
        )
        raise TermsNotConfiguredException()

    return CurrentTerms(version=settings.current_terms_version, url=settings.current_terms_url)
