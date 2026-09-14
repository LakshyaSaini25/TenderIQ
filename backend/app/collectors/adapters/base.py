"""
BaseSourceAdapter
-----------------
All source-specific adapters must inherit from this base class.

Each adapter knows how to:
  1. Check whether it supports a given source record.
  2. Discover tender listing/detail URLs from the source homepage.
  3. Extract structured opportunity data from a single page/item.

Adapters must NOT contain generic HTTP or HTML utilities.
Those live in fetcher.py and parser.py.

Adding a new source = creating a new file in this package.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseSourceAdapter(ABC):

    @classmethod
    @abstractmethod
    def supports(cls, source: Dict[str, Any]) -> bool:
        """
        Return True if this adapter can handle the given source document.
        Checked by AdapterRegistry. Keep the logic simple (URL pattern, type, name, etc.)
        """
        raise NotImplementedError

    @abstractmethod
    async def discover_listing_urls(self, source_url: str) -> List[str]:
        """
        Given the source's root URL, return a list of tender/opportunity URLs
        (or items that will be processed individually).

        For RSS sources this returns item URLs.
        For HTML listing pages this returns detail page hrefs.
        For API sources this returns endpoint URLs or item identifiers.
        """
        raise NotImplementedError

    @abstractmethod
    async def extract_opportunity(
        self, url: str, html_or_content: str, source_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Parse a single tender page/item and return a normalized dict
        matching the opportunity schema, or None if extraction fails.

        Fields that cannot be extracted must be set to None.
        Must never raise an exception — errors should be caught and
        logged internally, returning None.
        """
        raise NotImplementedError

