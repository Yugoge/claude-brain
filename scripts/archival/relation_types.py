"""
Central configuration for relation types.
Used across all validation and analysis scripts.
"""

# Asymmetric relation types that must be unidirectional
ASYMMETRIC_TYPES = {
    'example_of',
    'prerequisite_of',
    'extends',
    'generalizes',
    'specializes',
    'cause_of',
    'is_a',
    'has_subtype',
    'member_of',
    'applies_to',
    'used_in',
}

# Symmetric types that are allowed to be bidirectional
SYMMETRIC_TYPES = {
    'related_to',
    'contrasts_with',
    'complements',
    'analogous_to',
    'synonym',
    'antonym',
}

# All valid relation types (union of asymmetric and symmetric)
ALL_TYPES = ASYMMETRIC_TYPES | SYMMETRIC_TYPES