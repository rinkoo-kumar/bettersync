# Engineering Build Note: BetterSync Orchestrator
**BetterUp People Technology Take-Home Exercise**
*Candidate Submission*

---

## 1. Why This Slice?

The assignment presents three interconnected operational failures in BetterUp's onboarding experience:
1. Changes don't propagate (post-offer updates, off-cycle hires).
2. Bad data cascades (typos, unstandardized addresses).
3. Nobody's watching the gates (T-7 deadline misses).

We chose to build **Unified Change Propagation with Invariant Gatekeeping and Agentic Discrepancy Resolution** because:
* **Change propagation is where business risk is highest**: An unpropagated start date or address change results in lost laptops ($3,000+ per unit), courier reshipment fees, stalled Day 1 account access, and a stressful new-hire experience.
* **Point-to-point Zapier/n8n automations fail at scale**: They lack state awareness, idempotency, and semantic reasoning. When a candidate edits an address from "100 Main St Ste 400" to "100 Main Street #400", brittle regex breaks or spawns duplicate records.
* **Highest ROI for AI**: Using Claude as a targeted, deterministic exception resolver (via API or MCP) turns what used to be manual People Ops triage into automated, high-confidence resolutions while maintaining human signoff for high-risk ambiguities.

---

## 2. Key Design Decisions

### 2.1 Canonical Data Model & System of Record (SoR) Authority
* **Problem**: Different systems use differing field formats (e.g. Workday `worker_id`, Ashby `candidate_id`, Okta `login/email`, ExpoIT `order_id`).
* **Decision**: We created a single `HireProfile` canonical schema with strict Pydantic v2 validation. Workday is treated as the SoR for worker status and legal profile, while Ashby remains authoritative for pre-hire offer details. Every record computes a SHA-256 state fingerprint to detect drift across systems.

### 2.2 Strict Idempotency & Replay Protection
* **Problem**: Webhook retries, network blips, or manual button-mashing in People Ops portals often cause duplicate laptop orders or multiple Okta accounts.
* **Decision**: Every action generates an idempotency key derived from:
  $$\text{idempotency\_key} = \text{SHA256}(\text{hire\_id} + \text{target\_system} + \text{action} + \text{payload\_hash})$$
  Downstream connectors track processed keys. Replaying an identical webhook (demonstrated in Scenario 4) returns `ALREADY_PROCESSED` with zero redundant downstream calls.

### 2.3 Failure Handling & Transient Resilience
* **Decision**: Connectors implement simulated transient failure points (HTTP 429/503) with exponential backoff and jitter. In a live production environment, unrecoverable failures route to a Dead Letter Queue (DLQ) with original webhook headers preserved for manual or automated replay.

### 2.4 Cryptographic Append-Only Audit Trail
* **Decision**: We implemented a blockchain-style hash chain:
  $$\text{current\_hash} = \text{SHA256}(\text{record\_id} + \text{timestamp} + \text{diff} + \text{prev\_hash})$$
  This guarantees tamper evidence for compliance (SOC 2, GDPR, SOX). If any database record or diff is altered post-hoc, `verify_integrity()` immediately flags the discrepancy (verified in unit tests).

---

## 3. The Claude AI Component (Where & Why)

### Where Claude Fits
We explicitly avoided building "just a chatbot" or an unbounded LLM wrapper. Instead, Claude is embedded as a **narrow, bounded agentic decision handler**:
1. **Semantic Discrepancy Triage**: When upstream and downstream systems disagree on an address, name formatting, or phone number, Claude evaluates USPS postal standards and semantic equivalence.
2. **Confidence Thresholding**: If confidence $\ge 0.90$, the orchestrator auto-resolves and writes the change downstream. If $< 0.90$ (e.g., conflicting start dates between Ashby and a recruiter's Slack message), Claude drafts a formatted Slack triage card for People Ops signoff.
3. **Model Context Protocol (MCP)**: Implemented standard MCP tools (`get_hire_cross_system_state`, `compute_system_drift`, `resolve_discrepancy_and_sync`, `notify_people_ops_slack`) so Claude Desktop or Claude Code can act as an interactive People Ops co-pilot.

---

## 4. What We Would Productionize Next

If rolling this out to BetterUp's production infrastructure:
1. **Event Streaming Backbone**: Back the ingestion layer with Apache Kafka or AWS SQS/EventBridge with partitioned FIFO ordering per `hire_id` to guarantee strictly ordered event processing.
2. **Secret & Credential Management**: Integrate HashiCorp Vault or AWS Secrets Manager with automatic OAuth 2.0 token caching and mTLS rotation (see [SECURITY_AUTH.md](file:///D:/Projects/ai_assignment/SECURITY_AUTH.md)).
3. **Bi-directional Webhook Gateways**: Deploy signed webhook verifiers for Ashby and Workday RaaS (Report-as-a-Service) change notifications.
4. **Slack Block Kit Interactive Actions**: Add interactive buttons ("Approve Override", "Reject Change") to People Ops Slack notifications allowing one-click human-in-the-loop resolutions.

---

## 5. AI Reflection: What AI Got Wrong & How We Caught It

### AI Tools Used
* **Cursor & Claude Code**: Used for boilerplate scaffolding, test fixture generation, and schema mapping.

### What the AI Got Wrong
* **The Error**: During initial generation of the address reconciliation logic, the AI model proposed replacing downstream addresses with whichever payload arrived last (a naive Last-Write-Wins strategy) and using a basic string `strip().lower()` equality check.
* **Why It Was Dangerous**: 
  1. Address abbreviation variations (e.g. "Ste 400" in Ashby vs "Suite 400" in Workday) triggered false-positive overwrite cycles, causing infinite ping-pong sync loops between Ashby and Workday.
  2. Overwriting Workday's validated postal address with raw candidate input could break FedEx/UPS address validation in ExpoIT.
* **How We Caught and Fixed It**: 
  1. We caught it during test case formulation when testing "100 main street ste 400" against "100 Main St, Suite 400".
  2. We corrected it by introducing:
     - Canonical address normalization (`DataValidator.normalize_address`).
     - Explicit System of Record hierarchy rules.
     - Semantic equivalence evaluation with confidence scoring before triggering any downstream mutation.
