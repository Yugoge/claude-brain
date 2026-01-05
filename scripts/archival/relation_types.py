"""
Central configuration for relation types.
Used across all validation and analysis scripts.
"""

# Paired relation types (forward ⟷ reverse)
PAIRED_TYPES = {
    'example_of': 'has_example',
    'has_example': 'example_of',
    'prerequisite_of': 'depends_on',
    'depends_on': 'prerequisite_of',
    'extends': 'is_extended_by',
    'is_extended_by': 'extends',
    'generalizes': 'specializes',
    'specializes': 'generalizes',
    'cause_of': 'effect_of',
    'effect_of': 'cause_of',
    'is_a': 'has_subtype',
    'has_subtype': 'is_a',
    'member_of': 'has_member',
    'has_member': 'member_of',
    'used_in': 'uses',
    'uses': 'used_in',
    'part_of': 'has_part',
    'has_part': 'part_of',
    'applies_to': 'applied_by',
    'applied_by': 'applies_to',
    'caused_by': 'cause_of',
    'has_prerequisite': 'prerequisite_of',
    'used_by': 'uses',
    'defined_by': 'defines',
    'defines': 'defined_by'
}

# Asymmetric relation types that must be unidirectional (derived from PAIRED_TYPES)
ASYMMETRIC_TYPES = set(PAIRED_TYPES.keys())

# Symmetric types that are allowed to be bidirectional
SYMMETRIC_TYPES = {
    'related_to',
    'contrasts_with',
    'complements',
    'analogous_to',
    'synonym',
    'antonym',
}

# Lexical relation types (language-specific, no inverse pairs)
LEXICAL_TYPES = {
    'derivationally_related',
    'cognate',
    'collocates_with',
    'translation_of',
    'hypernym',
    'hyponym'
}

# All valid relation types (union of asymmetric, symmetric, and lexical)
ALL_TYPES = ASYMMETRIC_TYPES | SYMMETRIC_TYPES | LEXICAL_TYPES