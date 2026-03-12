# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an A-share quantitative trading software project currently in the requirements analysis phase. The repository contains comprehensive Software Requirements Specification (SRS) documentation following IEEE 830 standard, tailored for China's A-share market with specific regulatory and trading rule considerations.

**Current Phase**: The project is in Phase 3 (Validation & Finalization), conducting systematic requirements validation through expert reviews and compliance verification. All code development will commence after the SRS is finalized and approved.

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
├── regulations/           # Market-specific rules and compliance
│   └── a-share-rules.md  # Comprehensive A-share trading rules summary
└── validation/           # Requirements validation materials (current focus)
    ├── README.md         # Validation process and materials overview
    ├── requirement-validation-checklist.md
    ├── requirement-validation-report.md
    ├── compliance-verification-report.md
    └── templates/        # Review meeting templates
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

### Phase 2: Detailed Requirements Development ✓
- Refine data management requirements (priority function)
- Develop trading system functional requirements
- Define non-functional requirements
- Create requirements traceability matrix

### Phase 3: Validation & Finalization (Current Phase)
- Requirements review workshops (four专题评审材料包 prepared)
- Regulatory compliance verification (expert confirmation pending)
- Final document approval and sign-off

## High-Level Architecture

Based on the SRS and planned technical stack, the system will likely consist of the following subsystems:

### Core Subsystems (from SRS Section 3)
1. **Data Management Subsystem** (`REQ-DM-*`)
   - Real-time market data ingestion
   - Historical data storage and retrieval
   - Fundamental data management
   - Data quality monitoring

2. **Trading System Subsystem** (`REQ-TS-*`)
   - Strategy development and backtesting
   - Order management and execution
   - Algorithmic trading engine
   - Position and portfolio management

3. **Risk Management Subsystem** (`REQ-RM-*`)
   - Real-time risk monitoring
   - Compliance rule enforcement
   - Margin and leverage control
   - Stress testing

4. **User Interface & Reporting** (`REQ-UI-*`)
   - Dashboard and visualization
   - Performance reporting
   - Alert and notification system

### Technical Architecture
- **Primary Language**: Python 3.8+ for backend and quantitative libraries
- **Data Storage**: PostgreSQL (relational), InfluxDB/ClickHouse (time-series)
- **Message Queue**: RabbitMQ or Kafka for event-driven architecture
- **Frontend**: React or Vue.js with TypeScript
- **Deployment**: Linux servers with Docker containerization
- **APIs**: RESTful and WebSocket interfaces for real‑time data

### Expected Project Layout (Once Development Starts)
```
src/
├── data_management/      # Data ingestion, storage, quality
├── trading_engine/       # Order management, execution, algorithms
├── risk_management/      # Risk monitoring, compliance rules
├── strategies/           # Quantitative trading strategies
├── api/                  # REST and WebSocket APIs
├── webapp/               # Frontend application
└── infrastructure/       # Deployment, monitoring, CI/CD
```

## Development Environment Setup

*No development environment is yet configured.* When code development begins, typical setup will include:

1. **Python virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Dependency management**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Database setup**:
   - PostgreSQL for relational data
   - InfluxDB/ClickHouse for time‑series data
   - Redis for caching

4. **Frontend setup** (if using React/Vue):
   ```bash
   npm install
   ```

## Build, Test, and Lint Commands

*No build system or test suite exists yet.* Once implemented, expect commands similar to:

### Python Backend
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run tests for a specific module
pytest src/data_management/ -v

# Code formatting with black
black src/

# Linting with flake8
flake8 src/

# Type checking with mypy
mypy src/
```

### Frontend (if using React)
```bash
# Install dependencies
npm install

# Development server
npm start

# Build for production
npm run build

# Run tests
npm test

# Lint JavaScript/TypeScript
npm run lint
```

### Documentation
```bash
# Check Markdown formatting (if markdownlint is added)
npx markdownlint docs/**/*.md

# Spell check (if cspell is added)
npx cspell "docs/**/*.md"
```

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
- **docs/validation/README.md**: Requirements validation materials and process

## Important Notes

- This is a sensitive financial project - all documentation contains proprietary business information
- Regulatory compliance is critical - always verify requirements against current regulations
- The SRS serves as the foundation for future development - maintain accuracy and completeness
- Prioritize data management requirements as per project focus areas
- **No source code exists yet** - all work currently focuses on requirements validation