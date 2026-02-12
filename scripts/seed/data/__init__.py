# Data module for Downtown seed
from .categories_primary import DOWNTOWN_DATA_PRIMARY
from .categories_secondary import DOWNTOWN_DATA_SECONDARY

DOWNTOWN_DATA = {**DOWNTOWN_DATA_PRIMARY, **DOWNTOWN_DATA_SECONDARY}

__all__ = ['DOWNTOWN_DATA']
