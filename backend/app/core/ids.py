"""Shared parsing for resource identifiers taken from URL path parameters."""

from uuid import UUID

from app.core.exceptions import ResourceNotFoundError

# A canonical UUID text form is 8-4-4-4-12 hex digits joined by dashes.
UUID_TEXT_LENGTH = 36


def parse_uuid(raw_identifier: str, not_found_message: str) -> UUID:
    """Parse a canonical lowercase UUID or raise ``ResourceNotFoundError``.

    Rejects wrong-length input, non-UUID text, and non-canonical spellings
    (uppercase, unhyphenated, or ``urn:uuid:`` forms) so malformed path
    parameters surface as a not-found response instead of a parse error.
    """
    if len(raw_identifier) != UUID_TEXT_LENGTH:
        raise ResourceNotFoundError(not_found_message)
    try:
        identifier = UUID(raw_identifier)
    except ValueError:
        raise ResourceNotFoundError(not_found_message) from None
    if str(identifier) != raw_identifier.lower():
        raise ResourceNotFoundError(not_found_message)
    return identifier
