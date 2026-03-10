# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an A-share quantitative trading software project currently in the requirements analysis phase. The repository contains comprehensive Software Requirements Specification (SRS) documentation following IEEE 830 standard, tailored for China's A-share market with specific regulatory and trading rule considerations.

## Document Structure

The documentation is organized in a hierarchical structure:

```
docs/
├── srs/                    # Software Requirements Specification (IEEE 830)
│   ├── README.md          # SRS directory overview and table of contents
│   ├── section1-introduction.md      # Purpose, scope, definitions
│   ├── section2-overall-description.md # Product perspective, features, user characteristics
│   └── section3-specific-requirements.md # Functional and non-functional requirements
├── requirements/          # Supplementary requirements analysis
│   ├── stakeholder-analysis.md    # Identifies and analyzes all stakeholders
│   └── use-cases.md              # Detailed user scenarios and workflows
└── regulations/           # Market-specific rules and compliance
    └── a-share-rules.md  # Comprehensive A-share trading rules summary
```

## Key Architectural Concepts

### SRS Organization (IEEE 830 Standard)
- **Section 1: Introduction** - Project purpose, scope, definitions, references
- **Section 2: Overall Description** - Product perspective, functions, user classes, constraints
- **Section 3: Specific Requirements** - Functional requirements, non-functional requirements, interface requirements

### Requirement Identification System
All requirements follow a structured naming convention:
- `REQ-{SUBSYSTEM}-{SEQ}` for functional requirements (e.g., `REQ-DM-001` for Data Management)
- `REQ-PER-{SEQ}` for performance requirements
- `REQ-REL-{SEQ}` for reliability requirements
- `REQ-SEC-{SEQ}` for security requirements
- `REQ-IF-{SEQ}` for interface requirements
- `REQ-DC-{SEQ}` for design constraints
- `REQ-ATTR-{SEQ}` for software system attributes

### Priority Levels
- **P0 (Critical)**: Must be implemented for system to function
- **P1 (High)**: Important features affecting system completeness
- **P2 (Medium)**: Valuable but not essential features
- **P3 (Low)**: Nice-to-have features for future releases

## A-Share Market Specifics

The system must comply with China's A-share market regulations:
- **T+1 Settlement**: Stocks bought today cannot be sold until next trading day
- **Price Limits**: ±10% daily price movement limits (varies by board)
- **Trading Hours**: 9:30-11:30, 13:00-15:00 (with pre-market auction 9:15-9:25)
- **Regulatory Bodies**: CSRC (China Securities Regulatory Commission), SSE, SZSE
- **Data Sources**: Wind, Tushare, JoinQuant (local data vendors)

## Development Phases

### Phase 1: Requirements Collection & Framework Establishment ✓
- Create SRS document structure based on IEEE 830
- Stakeholder analysis and use case development
- A-share rules compilation
- Git repository initialization

### Phase 2: Detailed Requirements Development (Current Phase)
- Refine data management requirements (priority function)
- Develop trading system functional requirements
- Define non-functional requirements
- Create requirements traceability matrix

### Phase 3: Validation & Finalization
- Requirements review workshops
- Regulatory compliance verification
- Final document approval and sign-off

## Common Development Tasks

### Document Editing
- All documents use Markdown format with consistent heading structure
- When adding new requirements, follow the existing naming convention
- Update version history and status tables in relevant README files
- Maintain cross-references between documents

### Requirement Management
- New requirements should include: Description, Priority, Acceptance Criteria
- Update the SRS section3-specific-requirements.md for new functional requirements
- Ensure requirements have clear, measurable acceptance criteria
- Link requirements to relevant use cases in docs/requirements/use-cases.md

### Compliance Updates
- Regularly check for regulatory changes in A-share market rules
- Update docs/regulations/a-share-rules.md when regulations change
- Verify that requirements reflect current regulatory constraints

## Git Workflow

- **Main branch**: `master`
- **Commit messages**: Follow conventional commit format (feat:, docs:, fix:, etc.)
- **Document changes**: Include "Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>" in commit messages
- **Version tracking**: Document version numbers in docs/srs/README.md

## Technical Stack Reference

While currently a documentation project, the planned technical stack includes:
- **Primary Language**: Python 3.8+
- **Data Storage**: PostgreSQL (relational), InfluxDB/ClickHouse (time-series)
- **Message Queue**: RabbitMQ or Kafka
- **Frontend**: React or Vue.js
- **Deployment**: Linux servers, Docker containerization

## Quality Standards

### Document Quality
- Use clear, concise Chinese language for requirements documentation
- Maintain consistent formatting and structure across all documents
- Include practical examples and acceptance criteria for all requirements
- Ensure regulatory requirements are explicitly referenced and addressed

### Requirement Quality
- Requirements must be specific, measurable, achievable, relevant, and testable (SMART)
- Avoid ambiguity in requirement descriptions
- Include both functional and non-functional aspects
- Consider edge cases and error conditions

## Related Documentation

- **README.md**: High-level project overview and current status
- **docs/srs/README.md**: SRS document directory and version information
- **docs/requirements/stakeholder-analysis.md**: Complete stakeholder analysis
- **docs/requirements/use-cases.md**: Detailed user scenarios
- **docs/regulations/a-share-rules.md**: Comprehensive A-share market rules

## Important Notes

- This is a sensitive financial project - all documentation contains proprietary business information
- Regulatory compliance is critical - always verify requirements against current regulations
- The SRS serves as the foundation for future development - maintain accuracy and completeness
- Prioritize data management requirements as per project focus areas