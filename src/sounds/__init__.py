from enum import StrEnum, auto
from typing import Final


class FeatureFlags(StrEnum):
    # Items with the type single_item_promo are prominent currently-promoted items,
    # usually presented differently when viewed natively.
    SINGLE_ITEM_PROMO = auto()


FEATURE_FLAGS = {FeatureFlags.SINGLE_ITEM_PROMO: False}
VERBOSE_LOG_LEVEL: Final[int] = 5


def parse(json_dict: dict):
    """Parse an API response into an auntie-sounds output without the client."""
    from sounds.model_factory import ModelFactory

    return ModelFactory().parse_object(json_dict)
