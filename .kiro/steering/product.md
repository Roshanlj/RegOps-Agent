---
inclusion: always
---

# Product Overview

RegOps Copilot is an agentic QA/QC assistant for stability pull workflows in regulatory operations. It runs offline without requiring LLM API keys.

## Core Purpose

Automates repetitive, compliance-sensitive stability pull tasks:
- Fetching pull lists from LIMS
- Updating tracking sheets
- Creating Jira tickets
- Drafting QA emails with SOP citations
- Enforcing compliance checks (window validation, two-person review, required fields)

## Key Characteristics

- **Offline-first**: No external LLM dependencies
- **Deterministic**: Plan → Act → Review → Replan loop
- **Auditable**: Every action is logged for compliance
- **Rule-based**: Blocks actions if compliance checks fail
- **RAG-powered**: Grounds responses in ingested SOPs with citations

## Integration Points

All integrations are currently stubs for MVP:
- LIMS (Laboratory Information Management System)
- Google Sheets (tracking)
- Jira (ticketing)
- Email (notifications)

Real implementations would replace stub functions with live API integrations.
