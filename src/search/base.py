from abc import ABC, abstractmethod
from typing import List

from src.models import ImageCandidate


class SearchProviderException(Exception):
    """Base exception for search provider failures."""
    pass


class GoogleAntiBotException(SearchProviderException):
    """Raised when Google detects bot traffic and triggers CAPTCHA or sorry/index."""
    pass


class BaseImageSearcher(ABC):
    """Abstract base class for all image search providers."""

    @abstractmethod
    def search(self, keyword: str, max_results: int) -> List[ImageCandidate]:
        """
        Search for images matching the keyword.
        Returns a list of ImageCandidate objects.
        """
        pass
