# BetterSync: Enterprise Onboarding Orchestrator
> **BetterUp People Technology Take-Home Exercise**
> Submitted by: Candidate
> Reviewer: Jessica Brewer (`jessica.brewer@betterup.co`)

---

## Deliverables Index

| Deliverable | File Link | Description |
| :--- | :--- | :--- |
| **Deliverable 1: Systems Map** | [SYSTEMS_MAP.md](file:///D:/Projects/ai_assignment/SYSTEMS_MAP.md) | As-Is vs To-Be flows across Ashby, Workday, Okta, ExpoIT; failure analysis & slice rationale. |
| **Deliverable 2: Runnable Prototype** | [run_demo.py](file:///D:/Projects/ai_assignment/run_demo.py) | Full executable walkthrough across 5 realistic failure & resolution scenarios. |
| **Deliverable 3: Short Build Note** | [BUILD_NOTE.md](file:///D:/Projects/ai_assignment/BUILD_NOTE.md) | Key design decisions, data model, idempotency, failure recovery, and AI reflection. |
| **Bonus 1: MCP Server & Tool Specs** | [mcp_server.py](file:///D:/Projects/ai_assignment/mcp_server.py) / [mcp_tools.py](file:///D:/Projects/ai_assignment/src/agent/mcp_tools.py) | Standards-compliant Model Context Protocol server for Claude Desktop / Claude Code. |
| **Bonus 2: Security & Auth Blueprint** | [SECURITY_AUTH.md](file:///D:/Projects/ai_assignment/SECURITY_AUTH.md) | Enterprise OAuth 2.0 JWT bearer, Okta SSO, token caching, and HMAC webhook verification. |
| **Bonus 3: Cryptographic Audit Trail** | [audit_logger.py](file:///D:/Projects/ai_assignment/src/core/audit_logger.py) | Append-only SHA-256 hash chaining with automated tamper detection. |

---

## Quickstart (Under 2 Minutes)

### 1. Requirements & Setup
Python 3.10+ is required.

```powershell
# Clone or navigate to the repository
cd D:\Projects\ai_assignment

# Activate virtual environment
.venv\Scripts\Activate.ps1

# (Optional) If setting up fresh:
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### 2. Run the Interactive Terminal Demo
Executes all 5 core scenarios (Change Propagation, Claude Exception Triage, SLA Gate Breaches, Idempotent Replays, and Audit Trail Verification):

```powershell
python run_demo.py
```

### 3. Run the Automated Test Suite
Runs all 9 unit tests across reconciliation, SLA gate checks, Claude semantic resolution, and audit tamper detection:

```powershell
pytest -v
```

---

## Architectural Highlights

```
+-----------------------------------------------------------------------------------------+
|                                  BETTERSYNC ARCHITECTURE                                |
+-----------------------------------------------------------------------------------------+

  [ Ashby ATS ]       [ Workday Core HCM ]       [ Okta / Lumos ]       [ ExpoIT Hardware ]
        |                      |                        |                        |
        +----------------------+------------+-----------+------------------------+
                                            |
                                            v
                             +-----------------------------+
                             |  BetterSync Ingestion Core  |
                             |  - HMAC Signature Check     |
                             |  - Schema Normalization     |
                             |  - Hash-Based Idempotency   |
                             +-----------------------------+
                                            |
                     +----------------------+----------------------+
                     |                                             |
                     v                                             v
      +-----------------------------+               +-----------------------------+
      |   SLA Invariant Gatekeeper  |               |  Reconciliation & Diff Hub  |
      |   - T-7 Hardware Form Gate  |               |  - Detects multi-system lag |
      |   - T-7 Background Check    |               |  - Computes minimal delta   |
      |   - T-3 Okta Staging Gate   |               +-----------------------------+
      +-----------------------------+                              |
                     |                                             v
                     v                             +-------------------------------+
        [ Slack People Ops Alerts ]                | Claude Agentic Exception Triage|
                                                   | (API / MCP Protocol)          |
                                                   | - Semantic Equivalence Check  |
                                                   | - USPS Address Standardization|
                                                   | - Auto-Resolve or Slack Card  |
                                                   +-------------------------------+
                                                                   |
                                                                   v
                                                   +-------------------------------+
                                                   |  Tamper-Evident SHA-256 Audit |
                                                   +-------------------------------+
```

---

## Project Structure

```
ai_assignment/
├── README.md                  # Main overview & quickstart guide
├── SYSTEMS_MAP.md             # Deliverable 1: Systems map & failure point analysis
├── BUILD_NOTE.md              # Deliverable 3: Architectural decisions & AI reflections
├── SECURITY_AUTH.md           # Bonus: Enterprise OAuth 2.0 / SSO security model
├── pytest.ini                 # Pytest configuration
├── requirements.txt           # Python dependencies
├── run_demo.py                # Deliverable 2: Interactive CLI demo
├── mcp_server.py              # Bonus: Runnable Model Context Protocol server
├── data/
│   └── sample_scenarios.json  # Scenarios for start date shift, typo, SLA breach, off-cycle
├── src/
│   ├── models/
│   │   ├── canonical.py       # Canonical HireProfile, Address, Status enums
│   │   ├── events.py          # Event schemas, SyncAction, Discrepancy
│   │   └── audit.py           # Cryptographic audit model
│   ├── connectors/            # Mocked connectors with real enterprise schemas
│   │   ├── base.py            # Base connector with retry & idempotency tracking
│   │   ├── ashby.py           # Ashby ATS connector
│   │   ├── workday.py         # Workday HCM connector (supports off-cycle hires)
│   │   ├── okta.py            # Okta identity lifecycle connector
│   │   ├── expoit.py          # ExpoIT hardware ordering & shipment connector
│   │   └── cohort_tracker.py  # Cohort Tracker connector
│   ├── core/
│   │   ├── reconciler.py      # Core diff & idempotent propagation engine
│   │   ├── gatekeeper.py      # T-7, T-4, T-3 deadline watcher
│   │   ├── validator.py       # Pre-flight data quality & address normalizer
│   │   └── audit_logger.py    # Tamper-evident SHA-256 event chaining
│   ├── agent/
│   │   ├── claude_resolver.py # Claude agentic resolver (live API + deterministic fallback)
│   │   ├── mcp_tools.py       # MCP tool specifications
│   │   └── prompts.py         # System prompt & JSON schema
│   └── api/
│       └── app.py             # FastAPI webhook & dashboard endpoints
└── tests/
    ├── test_reconciliation.py # Idempotent sync & off-cycle tests
    ├── test_gatekeeper.py     # SLA deadline & milestone tests
    ├── test_claude_resolver.py# Claude semantic reasoning tests
    └── test_audit_trail.py    # SHA-256 tamper-evident integrity tests
```
