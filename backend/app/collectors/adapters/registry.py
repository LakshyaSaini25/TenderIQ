import logging
from typing import Dict, Any, List, Optional
from app.collectors.adapters.base import BaseSourceAdapter
from app.collectors.adapters.public_tender_adapter import PublicTenderAdapter
from app.collectors.adapters.eprocure_adapter import EprocureAdapter

logger = logging.getLogger(__name__)

class AdapterRegistry:
    _adapters: List[BaseSourceAdapter] = [
        EprocureAdapter(),
        PublicTenderAdapter()
    ]

    @classmethod
    def get_adapter_for_source(cls, source: Dict[str, Any]) -> BaseSourceAdapter:
        """
        Iterates over registered adapters and returns the first one that supports the source.
        Defaults to PublicTenderAdapter if no specific adapter claims it.
        """
        for adapter in cls._adapters:
            if adapter.supports(source):
                return adapter
        
        logger.info(f"No specific adapter claimed source {source.get('name')}. Defaulting to PublicTenderAdapter.")
        return PublicTenderAdapter()
