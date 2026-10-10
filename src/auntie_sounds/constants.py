# Schedule dates are UK broadcast days
from enum import StrEnum, auto
from typing import Final
from zoneinfo import ZoneInfo


class FeatureFlags(StrEnum):
    # Items with the type single_item_promo are prominent currently-promoted items,
    # usually presented differently when viewed natively.
    SINGLE_ITEM_PROMO = auto()


SCHEDULE_TIMEZONE = ZoneInfo("Europe/London")
FEATURE_FLAGS = {FeatureFlags.SINGLE_ITEM_PROMO: False}
VERBOSE_LOG_LEVEL: Final[int] = 5
