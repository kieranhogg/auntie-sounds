from enum import StrEnum, auto


class FeatureFlags(StrEnum):
    # Items with the type single_item_promo are prominent currently-promoted items,
    # usually presented differently when viewed natively.
    SINGLE_ITEM_PROMO = auto()


FEATURE_FLAGS = {FeatureFlags.SINGLE_ITEM_PROMO: False}
