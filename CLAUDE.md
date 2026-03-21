# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an A-share quantitative trading software project. The repository contains comprehensive Software Requirements Specification (SRS) documentation following IEEE 830 standard, tailored for China's A-share market with specific regulatory and trading rule considerations.

**Current Phase**: First Iteration Development (Data Management Subsystem) - In Progress (2026.4.3 - 2026.4.17)
- ✅ Requirements Analysis Phase - Fully Completed
- ✅ Architecture Design Phase - Fully Completed (v1.1 approved)
- ✅ Detailed Design Phase - Fully Completed (v1.2 approved for 6 core subsystems)
- 🚀 **Current**: Development of Data Management Subsystem - In Progress

## Project Structure

The project is organized as:

```
stock/
├── src/                     # Source code
│   ├── __init__.py
│   ├── common/              # Common utilities and base modules
│   ├── data_management/     # Data management subsystem (current focus)
│   ├── strategy_research/   # Strategy research and backtesting
│   ├── trading_engine/      # Trading engine and order execution
│   ├── risk_management/     # Risk management and compliance
│   ├── user_interface/      # Web UI and API routes
│   └── system_management/   # System configuration and monitoring
├── tests/                   # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   ├── performance/        # Performance and benchmark tests
│   ├── conftest.py         # pytest configuration
│   └── pytest.ini          # pytest settings
├── docs/                    # Project documentation
│   ├── srs/                # Software Requirements Specification (IEEE 830)
│   ├── architecture/       # Architecture design documents
│   ├── detailed-design/    # Detailed design documents
│   ├── requirements/       # Requirements analysis
│   ├── regulations/        # Regulatory compliance documents
│   └── validation/         # Review and validation materials
├── scripts/                 # Operational scripts
├── config/                  # Configuration files
├── deployment/              # Deployment configurations
├── data/                    # Local test data
├── logs/                    # Application logs
├── reports/                 # Test and benchmark reports
├── requirements.txt         # Python dependencies
├── pyproject.toml          # Project configuration (black, isort, mypy, pytest)
├── .pre-commit-config.yaml # pre-commit hooks configuration
├── .env.example            # Environment variables template
└── README.md               # Project overview
```

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
└── validation/           # Requirements validation materials
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

### Phase 3: Validation & Finalization ✓
- Requirements review workshops (four专题评审材料包 completed)
- Regulatory compliance verification (expert confirmation obtained)
- Final document approval and sign-off completed

### Phase 4: Architecture Design ✓
- Overall system architecture design
- Database schema design
- Interface contract definition
- Architecture v1.1 approved by technical review

### Phase 5: Detailed Design ✓
- 6 core subsystems detailed design
- Module interaction design
- Error handling and recovery design
- Detailed design v1.2 approved

### Phase 6: Development (Current Phase)
- **Iteration 1**: Data Management Subsystem development (2026.4.3 - 2026.4.17) - In Progress
- **Iteration 2**: Strategy Research Subsystem development (2026.4.18 - 2026.5.2) - Planned
- **Iteration 3**: Trading Engine Subsystem development (2026.5.3 - 2026.5.17) - Planned
- **Iteration 4**: Full system integration (2026.5.18 - 2026.6.1) - Planned

## High-Level Architecture

The system consists of the following core subsystems:

### Core Subsystems
1. **Data Management Subsystem** (`src/data_management/`)
   - Real-time market data ingestion
   - Historical data storage and retrieval
   - Fundamental data management
   - Data quality monitoring

2. **Strategy Research Subsystem** (`src/strategy_research/`)
   - Strategy development framework
   - Backtesting engine
   - Performance analysis and evaluation
   - Parameter optimization

3. **Trading Engine Subsystem** (`src/trading_engine/`)
   - Order management and execution
   - Algorithmic trading engine
   - Position and portfolio management
   - Order routing and execution

4. **Risk Management Subsystem** (`src/risk_management/`)
   - Real-time risk monitoring
   - Compliance rule enforcement
   - Margin and leverage control
   - Stress testing

5. **User Interface Subsystem** (`src/user_interface/`)
   - FastAPI RESTful endpoints
   - WebSocket for real-time data
   - Dashboard and visualization
   - Alert and notification system

6. **System Management Subsystem** (`src/system_management/`)
   - System configuration
   - Monitoring and logging
   - Scheduled task management
   - User and permission management

### Technical Architecture
- **Primary Language**: Python 3.10+ for backend and quantitative libraries
- **Data Storage**: PostgreSQL (relational), ClickHouse/InfluxDB (time-series), Redis (caching)
- **Message Queue**: Kafka for event-driven architecture
- **Web Framework**: FastAPI with Uvicorn
- **Deployment**: Linux servers with Docker containerization
- **APIs**: RESTful and WebSocket interfaces for real-time data

## Development Environment Setup

1. **Python virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Dependency management**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

4. **Environment configuration**:
   ```bash
   cp .env.example .env
   # Edit .env to set your database connection strings and other configuration
   ```

5. **Database setup** (for development):
   Start the test databases using Docker Compose:
   ```bash
   docker-compose -f docker-compose.test.yml up -d
   ```
   - PostgreSQL for relational data
   - ClickHouse and InfluxDB for time-series data
   - Redis for caching

6. **Frontend**: Not yet implemented

## Build, Test, and Lint Commands

### Python Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests with coverage report
pytest

# Run tests for a specific module
pytest tests/unit/data_management/ -v

# Run a specific test file
pytest tests/unit/data_management/test_ingestion.py -v

# Run tests without coverage for faster development
pytest --no-cov

# Code formatting with black
black src/ tests/

# Sort imports with isort
isort src/ tests/

# Linting with flake8
flake8 src/ tests/

# Type checking with mypy
mypy src/

# Run all pre-commit checks
pre-commit run --all-files
```

### Starting the Application

```bash
# Start development server
uvicorn user_interface.app:app --reload --host 0.0.0.0 --port 8000
```

### Documentation
```bash
# Check Markdown formatting (if markdownlint is installed)
npx markdownlint docs/**/*.md

# Spell check (if cspell is installed)
npx cspell "docs/**/*.md"
```

### Starting Test Databases

```bash
# Start all test databases in background
docker-compose -f docker-compose.test.yml up -d

# Stop all test databases
docker-compose -f docker-compose.test.yml down

# View logs from test databases
docker-compose -f docker-compose.test.yml logs -f
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

**Actual technical stack in use:**
- **Primary Language**: Python 3.10+
- **Web Framework**: FastAPI 0.109+, Uvicorn 0.27+
- **Data Processing**: pandas 2.2+, numpy 1.26+, scipy 1.11+, scikit-learn 1.4+
- **Data Storage**:
  - PostgreSQL (relational data) with SQLAlchemy 2.0+
  - ClickHouse (large-scale time-series market data)
  - InfluxDB (real-time market data)
  - Redis (caching)
- **Data Sources**: Tushare (Wind and JoinQuant require proprietary licenses)
- **Message Queue**: Kafka for event-driven architecture
- **Technical Analysis**: TA-Lib 0.4.28
- **Authentication**: python-jose, bcrypt, passlib
- **Code Quality**: black, isort, flake8, mypy, pre-commit
- **Testing**: pytest with pytest-asyncio, pytest-cov, factory-boy
- **Deployment**: Linux servers, Docker containerization
- **Frontend**: Not yet implemented

## Code Quality Standards

### Python Code Quality
- Follow PEP 8 style guidelines (enforced by flake8)
- Format code with black (line length 120)
- Sort imports with isort (black profile)
- Add type hints to all function signatures (checked by mypy in strict mode)
- Minimum 80% test coverage required for all modules
- All tests must pass before merging

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
- **docs/srs/section3-specific-requirements.md**: Functional and non-functional requirements
- **docs/requirements/stakeholder-analysis.md**: Complete stakeholder analysis
- **docs/requirements/use-cases.md**: Detailed user scenarios
- **docs/regulations/a-share-rules.md**: Comprehensive A-share market rules
- **docs/validation/README.md**: Requirements validation materials and process
- **docs/architecture/**: Architecture design documents
- **docs/detailed-design/**: Detailed module design documents

## Important Notes

- This is a sensitive financial project - all documentation and source code contains proprietary business information
- Regulatory compliance is critical - always verify new features against current A-share regulations
- The SRS serves as the foundation for development - maintain requirements traceability
- **Current focus**: Data Management Subsystem development (Iteration 1)
- Always run pre-commit checks before committing code
- All tests must pass and coverage requirements must be met before merging pull requests