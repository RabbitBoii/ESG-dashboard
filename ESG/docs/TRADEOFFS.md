# TRADEOFFS.md — What Was Deliberately Not Built

Three things left out, why, and what the real implementation would look like.

---

## 1. Real-time API Ingestion (SAP OData, Concur API, Green Button XML)

**What was built instead:** File upload (CSV drag-and-drop) for all three sources.

**Why it was left out:**
- SAP OData integration requires the client's SAP system to have Gateway enabled and a custom service exposed. This is an IT project on the client side, not something a prototype can mock meaningfully. A fake OData endpoint would test nothing real.
- Concur's API requires OAuth 2.0 with employer-specific tenant configuration, token refresh handling, and pagination across potentially thousands of trip records. The data shape of a Concur CSV export is identical to what the API returns — the parser is the same either way. The OAuth layer is pure plumbing that adds complexity without demonstrating anything about emissions data handling.
- Green Button (NAESB REQ.21) is the US utility data standard — XML-based, with a specific schema. Supporting it properly requires an XML parser and schema validation layer. For Indian enterprise clients (which this prototype targets), Green Button is irrelevant — Indian DISCOMs don't support it.

**What the real implementation would look like:**
- SAP: a scheduled ABAP extraction job runs nightly, drops a flat file to an SFTP endpoint, the ingestion service polls and processes it
- Concur: OAuth flow at client onboarding, nightly pull via `/travel/trip/v1.1/list` with date range filter, incremental sync
- Utility: Green Button Connect My Data (CMD) OAuth flow for US clients; for Indian clients, a portal scraper or manual upload remains the realistic path for 2024

---

## 2. Multi-user Roles (Analyst vs Admin vs Client Portal)

**What was built instead:** Single user type, no authentication. Any user can upload and review.

**Why it was left out:**
- Implementing auth properly (JWT or session-based, password hashing, token refresh, protected routes on both frontend and backend) is 1–2 days of work that doesn't demonstrate anything about the core problem — emissions data ingestion and normalization.
- Role-based access control (RBAC) adds another layer: defining permissions, enforcing them at the view level, testing edge cases. This is standard Django work but not what this assignment is evaluating.
- A prototype with fake auth (hardcoded tokens, no real session management) would be worse than no auth — it creates false confidence without real security.

**What the real implementation would look like:**
- Three roles: `CLIENT_UPLOADER` (can upload CSVs for their client only), `ANALYST` (can review and approve records), `AUDITOR` (read-only, can see approved records and audit logs)
- Django's built-in auth + DRF's permission classes handle this cleanly
- Client isolation enforced at the permission layer, not just the queryset layer
- Frontend: protected routes, role-based UI (auditors don't see approve/reject buttons)

---

## 3. Emission Factor Versioning UI and Multi-year Reporting

**What was built instead:** Seeded emission factors, not editable via the app. Single year of data.

**Why it was left out:**
- Emission factors change annually (DEFRA publishes updates every year, CEA publishes India grid intensity annually). A proper versioning system needs `valid_from`/`valid_to` date ranges on factors, logic to pick the correct factor for a given activity date, and a UI for Breathe ESG staff to update factors each year.
- The data model already has `valid_from` and `valid_to` fields on `EmissionFactor` — the foundation is there. Building the UI and the factor-selection logic was cut for time.
- Multi-year reporting (comparing Scope 1 emissions across 2022, 2023, 2024 using the correct factor for each year) is a significant feature that requires the versioning system as a prerequisite.

**What the real implementation would look like:**
- Admin UI (Django admin or custom) for Breathe ESG staff to add new factor versions each year
- Normalization logic selects the factor where `valid_from <= activity_date <= valid_to` (or `valid_to IS NULL` for the current factor)
- Re-normalization job that re-calculates `normalized_value` for all approved records when a factor is retroactively corrected
- Annual comparison dashboard showing YoY emissions trends per scope and source

---

## What This Means for the Prototype

The three omissions are intentional scope decisions, not gaps in understanding. The file upload mechanism produces identical parsed data to what a real API integration would produce — the parser, normalizer, data model, and review workflow are all production-representative. Auth and factor versioning are standard engineering work that would be added in a real v1, but don't change the core architecture documented in MODEL.md.