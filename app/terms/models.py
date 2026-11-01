from dataclasses import dataclass


@dataclass(frozen=True)
class CurrentTerms:
    """The terms version users currently have to accept, plus where its text lives.
    No table - both values come from the config."""

    version: str
    url: str
