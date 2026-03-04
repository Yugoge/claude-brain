# ISCED-F 2013 Taxonomy System

This directory contains the UNESCO International Standard Classification of Education - Fields (ISCED-F 2013).

## Classification System

### ISCED-F 2013
International Standard Classification of Education - Fields
- 3-level hierarchy: Broad (2-digit) → Narrow (3-digit) → Detailed (4-digit)
- Used for educational programs and qualifications
- Reference: [isced-index.md](./isced-index.md)

## Structure

```
_taxonomy/
├── index.md                                    (this file)
├── isced-index.md                              (ISCED broad fields list)
├── 00-generic-programmes-and-qualifications/
│   ├── index.md
│   └── [narrow-field].md
├── 01-education/
├── 02-arts-and-humanities/
├── 03-social-sciences-journalism-and-information/
├── 04-business-administration-and-law/
├── 05-natural-sciences-mathematics-and-statistics/
├── 06-information-and-communication-technologies-icts/
├── 07-engineering-manufacturing-and-construction/
├── 08-agriculture-forestry-fisheries-and-veterinary/
├── 09-health-and-welfare/
└── 10-services/
```

## Purpose

This taxonomy is used by the classification-expert agent to determine the appropriate knowledge domain for user questions and to organize Rems into the correct ISCED-based folder structure in the knowledge base.
