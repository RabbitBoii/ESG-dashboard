# DECISIONS.md — Ambiguities Resolved

Every non-obvious choice made during this build, what was chosen, why, and what I'd ask the PM if I could.

---

## Ingestion Mechanism

### Decision: File upload for all three sources (not API pull)

**Chosen:** CSV file upload via drag-and-drop for SAP, Utility, and Travel data.

**Why:**
- SAP does not expose a REST API to external systems by default. Real SAP integrations require middleware (SAP PI/PO, BTP Integration Suite) or ABAP custom extraction jobs — none of which are mockable in a 4-day prototype without access to an actual SAP system.
- Utility portals (MSEDCL, Tata Power, PG&E etc.) have inconsistent or non-existent APIs. The dominant real-world pattern is a facilities manager logging into a portal and downloading a CSV.
- Concur/Navan do have APIs, but OAuth credential management, token refresh, and rate limiting are out of scope for a prototype. The data shape of a Concur CSV export is identical to what the API returns — the parser is the same either way.
- File upload is also the honest answer for what a sustainability lead actually does today: they get a file, they upload it. Building a fake API pull would add complexity without reflecting reality.

**What I'd ask the PM:**
- "Do any of these clients have live API access already configured? If yes, which source should we prioritise for real-time pull in v2?"
- "Is the expectation that clients upload themselves, or does a Breathe ESG analyst do the upload on their behalf?"

---

## SAP Format Choice

### Decision: Flat file CSV export from ME2M/ME2L transaction, not IDoc or OData

**Chosen:** Tab/comma-separated flat file export from SAP purchasing transactions (ME2M by material, ME2L by delivery date).

**Why:**
- IDoc is SAP's EDI format — it's used for system-to-system integration (SAP to SAP, SAP to 3PL). It requires a receiving ALE/EDI layer to parse. No sustainability platform would receive IDocs as their primary ingestion path.
- OData (SAP Gateway) requires the client's SAP system to have Gateway enabled and the right service exposed — common in S/4HANA but not universal in ECC deployments, and requires authenticated API access.
- Flat file export (System > List > Save > Local File in ALV Grid) is what every SAP user already knows how to do. It requires zero IT involvement from the client. This is the realistic path for an enterprise onboarding in 2024.

**Subset handled:**
- Fuel and energy procurement only (material groups: diesel, heating oil, natural gas, LPG)
- Purchase order line items from EKKO/EKPO tables
- German column headers supported (mapped via a hardcoded header alias dictionary in the parser)

**Explicitly ignored:**
- Production orders and process orders (PP module) — different export format
- Asset-based fuel tracking (PM module)
- Goods receipts vs purchase orders distinction — using PO date as activity date

**What I'd ask the PM:**
- "Is the client on ECC or S/4HANA? S/4HANA has a dedicated Sustainability Footprint Management module that exports directly to kgCO2e — we might not need to normalize at all."
- "How does the client classify fuel materials in their SAP? Do they use standard material groups or custom ones? We need their material-to-fuel-type mapping."

---

## Utility Data Format Choice

### Decision: Portal CSV export, not PDF bill or Green Button XML

**Chosen:** CSV export from utility portal (MSEDCL/Tata Power style for Indian clients).

**Why:**
- PDF bills require OCR — fragile, format changes per utility, and accuracy degrades on scanned bills. Not appropriate for data that goes to auditors.
- Green Button (XML) is the US standard — relevant for US clients but not Indian enterprise clients, which is what the sample data reflects.
- Portal CSV is what facilities managers actually download. It's structured, consistent per utility, and doesn't require OCR.

**Subset handled:**
- Consumption-based rows (meter read start/end or direct consumption figure)
- Units: kWh and MWh (MWh normalised to kWh before emission calculation)
- Billing period stored as-is — not split across calendar months (see billing period decision below)

**Explicitly ignored:**
- Demand charges (kVA) — not relevant for emissions calculation
- Power factor penalties — financial, not emissions-relevant
- Reactive energy (kVAh) — out of scope for Scope 2 calculation

### Decision: Billing periods are NOT split across calendar months

**Chosen:** Store the billing period start and end as-is. Set `activity_date` to billing period start. Do not prorate consumption across months.

**Why:**
- Prorating requires assumptions (linear consumption across the period) that introduce error. A factory doesn't consume electricity uniformly — it may have shutdowns mid-period.
- For annual emissions totals (what auditors care about), the difference is zero if you're consistent. Jan 3 – Feb 1 consumption still gets counted once.
- The complexity of splitting adds code with no accuracy benefit for annual reporting.

**What I'd ask the PM:**
- "Do clients need monthly breakdowns for internal tracking, or just annual totals for audit? If monthly, we need to either ask clients to pull monthly-aligned data or implement prorating with an explicit assumption logged."

---

## Travel Data Format Choice

### Decision: Concur-style CSV export, not Navan API

**Chosen:** CSV export in the shape of a Concur Travel & Expense report export.

**Why:**
- Concur is the dominant corporate travel platform in enterprise. Navan is newer and growing but less common in the large enterprise segment Breathe ESG targets.
- Both platforms export CSVs in structurally similar formats (trip ID, employee, category, origin, destination, amount). The parser handles either.
- Navan's API requires OAuth and employer-specific tenant configuration — same argument as the SAP API decision above.

**Subset handled:**
- Flights (origin/destination IATA codes, cabin class)
- Hotels (nights, vendor name)
- Ground transport (distance in km, vendor)

**Explicitly ignored:**
- Rail travel — different emission factor, not in sample data
- Car rentals — would need fuel type and distance, rarely available
- Per-diem meals — not emissions-relevant

### Decision: Missing cabin class defaults to Economy

**Chosen:** If `cabin_class` is NULL or empty in the source row, treat as Economy for emission factor purposes.

**Why:**
- Economy is the conservative (lower) estimate. Defaulting to Business would overstate emissions.
- The flag `["cabin_class_assumed"]` is added to the record so an analyst can review and correct if they know the actual class.

**What I'd ask the PM:**
- "What's the client's policy on cabin class? Some companies only allow economy — if that's the case, defaulting to economy is not just a fallback but a policy reflection."

### Decision: Airport distances from a seeded lookup table, not a live API

**Chosen:** Pre-seeded `AirportDistance` table covering routes in the sample data. Unknown routes fall back to the Haversine formula using hardcoded airport coordinates.

**Why:**
- A live aviation distance API (like AviationStack or similar) adds a dependency, rate limits, and cost.
- The GHG Protocol uses great-circle distance with a 9% uplift factor for routing inefficiency. This is calculable offline.
- For a prototype, seeded + haversine is accurate enough and has zero external dependencies.

**What I'd ask the PM:**
- "How many unique routes does the client have per year? If it's hundreds of international routes, we need an API. If it's 20-30 domestic routes, the lookup table scales fine."

---

## Scope Assignment

### Decision: Scope is set by the parser per source type, but stored as an independent field

**Chosen:** SAP parser sets scope=1, Utility parser sets scope=2, Travel parser sets scope=3 — but scope is a standalone field on EmissionRecord, not derived from source_type at query time.

**Why:**
- In this prototype the mapping is coincidental — these three sources happen to map 1:1 to the three scopes.
- In production, SAP procurement data (purchased goods, logistics) is Scope 3. A client with on-site solar or CHP would have Scope 1 utility data. Encoding the mapping as a derivation would be a model error we'd have to undo.
- Storing scope explicitly costs one column and future-proofs the model completely.

---

## Status Flow

### Decision: Linear status flow, no re-submission

**Chosen:** `PENDING → APPROVED | FLAGGED | REJECTED`. A flagged record can be moved to approved or rejected. Rejected records are final.

**Why:**
- Re-submission (reject → re-ingest → re-approve) would require versioning of emission records, which adds significant complexity.
- In practice, a rejected row means the source data was wrong. The fix is to correct the source file and re-upload as a new batch — not to edit the rejected record in place.
- If an analyst needs to correct a value before approving, they can edit the `normalized_value` (which is logged in AuditLog) and then approve.

---

## What I Would Ask the PM (Consolidated)

1. "Is this client on SAP ECC or S/4HANA? The export format and available data differ significantly."
2. "Who does the upload — the client's sustainability lead, or a Breathe analyst on their behalf? This changes the UX requirements."
3. "Do clients need monthly emissions breakdowns or just annual totals? This determines whether we need to split cross-month utility billing periods."
4. "How many unique travel routes does the client have? This determines whether we need a live distance API or a lookup table scales."
5. "Is there an existing chart of accounts or material classification in SAP we can reference to map materials to fuel types, or do we build our own mapping?"
