# MODEL.md — Breathe ESG Data Model

## Overview

The data model is designed around one core insight: **raw data and normalized data must never be conflated.** Every ingested row preserves its original form permanently. Normalization happens lazily — only when an analyst triggers review — so the system always has a clear source-of-truth and analysts can see exactly what transformation was applied to each value.

---

## Design Decisions (Summary)

| Decision | Choice | Why |
|---|---|---|
| Multi-tenancy | Single DB, `client_id` FK on every table | Standard SaaS pattern; simple to implement, easy to query, no cross-client bleed if enforced at the ORM layer |
| Audit trail | Full edit log — every status change AND value edit logged | Auditors need to know not just what was approved, but what was changed before approval |
| Normalization | Lazy — store raw first, normalize on analyst review | Raw data is immutable source-of-truth; normalization logic can be updated without re-ingestion |
| Scope assignment | Separate field from source type | SAP could contain Scope 3 procurement data in future; hardcoding SAP=Scope1 would be wrong |

---

## Entity Relationship (Conceptual)

```
Client
  └── IngestionBatch (one per file upload)
        └── EmissionRecord (one per CSV row)
              └── AuditLog (one per status change or edit)

Client
  └── PlantLookup (SAP plant code → facility name)

EmissionFactor (global, not per-client)
```

---

## Tables

### 1. `Client`

Represents an enterprise customer of Breathe ESG. Every data row in the system belongs to a client.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `name` | VARCHAR(255) | Company name |
| `slug` | VARCHAR(100) | URL-safe identifier e.g. `acme-corp` |
| `created_at` | TIMESTAMP | |
| `is_active` | BOOLEAN | Soft-delete |

**Why UUID over auto-increment?** Client IDs will appear in API responses and URLs. UUIDs prevent enumeration attacks and are safe to expose.

---

### 2. `IngestionBatch`

One record per file upload event. Tracks the provenance of every ingested dataset — who uploaded it, when, from which source, and what happened during parsing.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `client` | FK → Client | |
| `source_type` | ENUM | `SAP`, `UTILITY`, `TRAVEL` |
| `uploaded_by` | FK → User | Django auth user |
| `uploaded_at` | TIMESTAMP | |
| `original_filename` | VARCHAR(255) | Stored for traceability |
| `row_count_total` | INTEGER | Total rows in the file |
| `row_count_success` | INTEGER | Rows that parsed cleanly |
| `row_count_failed` | INTEGER | Rows that failed parsing |
| `status` | ENUM | `PROCESSING`, `COMPLETE`, `FAILED` |
| `notes` | TEXT | Optional analyst note at upload time |

**Why track row counts here?** An analyst reviewing a batch needs to know upfront if 200 of 800 rows failed — that's a signal to investigate the source file, not just approve the 600 that came through.

---

### 3. `ParseFailure`

Rows that could not be parsed into an `EmissionRecord`. Stored separately so they're visible in the dashboard and can be investigated without cluttering the main records table.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `batch` | FK → IngestionBatch | |
| `client` | FK → Client | Denormalized for query convenience |
| `row_number` | INTEGER | Line number in the original file |
| `raw_row` | JSONB | The exact row that failed |
| `failure_reason` | VARCHAR(500) | Human-readable reason e.g. `"Missing required field: MENGE"` |
| `created_at` | TIMESTAMP | |

---

### 4. `EmissionRecord`

The core table. One row per successfully parsed line item from any source. Stores both the raw original values and (once reviewed) the normalized kgCO2e value.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `client` | FK → Client | |
| `batch` | FK → IngestionBatch | |
| `source_type` | ENUM | `SAP`, `UTILITY`, `TRAVEL` — where the data came from |
| `scope` | ENUM | `1`, `2`, `3` — GHG Protocol scope |
| `activity_date` | DATE | Date of the activity (not ingestion date) |
| `description` | VARCHAR(500) | Human-readable label e.g. `"Diesel - Plant 1000"` |
| `raw_value` | DECIMAL(15,4) | Exactly as it appeared in the source file |
| `raw_unit` | VARCHAR(20) | Exactly as it appeared e.g. `L`, `KG`, `M3`, `kWh`, `MWh` |
| `normalized_value` | DECIMAL(15,4) | In kgCO2e — NULL until normalization runs |
| `normalized_at` | TIMESTAMP | When normalization was applied |
| `emission_factor_used` | FK → EmissionFactor | Which factor was used, for traceability |
| `raw_row` | JSONB | The complete original CSV row, never modified |
| `status` | ENUM | `PENDING`, `APPROVED`, `FLAGGED`, `REJECTED` |
| `flags` | JSONB | Array of flag codes e.g. `["unit_ambiguous", "outlier"]` |
| `reviewed_by` | FK → User | NULL until reviewed |
| `reviewed_at` | TIMESTAMP | NULL until reviewed |
| `created_at` | TIMESTAMP | |

**Why store `raw_row` as JSONB?** Auditors and analysts will ask "what exactly came in?" at any point. Storing the original row means we can always answer that question without touching the source file. It's immutable — never updated after creation.

**Why is `normalized_value` nullable?** Normalization is lazy. A record enters the system as `PENDING` with raw values only. When an analyst opens it for review, normalization runs (or they can trigger it manually). This means normalization logic can be improved and re-run without re-ingesting the source file.

**Why separate `source_type` from `scope`?** These are independent dimensions. In the current prototype they map 1:1 (SAP→Scope1, UTILITY→Scope2, TRAVEL→Scope3) but this is a coincidence of the dataset, not a rule. SAP procurement data could be Scope 3 (purchased goods). A client with on-site solar generation would have Scope 1 utility data. Hardcoding the mapping would be a model mistake.

---

### 5. `AuditLog`

Tracks every change to an `EmissionRecord` — status transitions and value edits. This is the full audit trail required for ESG reporting.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `record` | FK → EmissionRecord | |
| `client` | FK → Client | Denormalized for query convenience |
| `changed_by` | FK → User | |
| `changed_at` | TIMESTAMP | |
| `action` | ENUM | `STATUS_CHANGE`, `VALUE_EDIT`, `FLAG_ADDED`, `FLAG_REMOVED` |
| `field_name` | VARCHAR(100) | Which field changed e.g. `"normalized_value"`, `"status"` |
| `old_value` | TEXT | Previous value as string |
| `new_value` | TEXT | New value as string |
| `comment` | TEXT | Optional analyst note explaining the change |

**Why log old and new values as TEXT?** The log needs to be readable by auditors who are not engineers. Storing `"8058"` → `"7900"` with `field_name="raw_value"` is immediately understandable without needing to join other tables or understand the schema.

---

### 6. `EmissionFactor`

Lookup table for emission conversion factors. Sourced from DEFRA 2023 guidelines.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `material_code` | VARCHAR(100) | e.g. `DIES-001`, `ERGAS-H`, `ELECTRICITY_IN`, `FLIGHT_ECONOMY` |
| `material_name` | VARCHAR(255) | Human readable e.g. `"Diesel"`, `"India Grid Electricity"` |
| `scope` | ENUM | `1`, `2`, `3` |
| `factor_value` | DECIMAL(10,6) | kgCO2e per unit |
| `factor_unit` | VARCHAR(20) | The denominator unit e.g. `per_litre`, `per_kwh`, `per_km` |
| `source` | VARCHAR(255) | e.g. `"DEFRA 2023"` |
| `valid_from` | DATE | Factors change year to year |
| `valid_to` | DATE | NULL = currently active |

**Seeded values used in this prototype:**

| Material | Factor | Unit | Source |
|---|---|---|---|
| Diesel | 2.68 | kgCO2e/litre | DEFRA 2023 |
| Heating Oil | 2.52 | kgCO2e/litre | DEFRA 2023 |
| Natural Gas | 2.04 | kgCO2e/m³ | DEFRA 2023 |
| LPG | 1.56 | kgCO2e/kg | DEFRA 2023 |
| Electricity (India grid) | 0.82 | kgCO2e/kWh | CEA 2023 |
| Flight (Economy) | 0.255 | kgCO2e/km/passenger | DEFRA 2023 |
| Flight (Business) | 0.765 | kgCO2e/km/passenger | DEFRA 2023 (3x economy) |
| Hotel night | 31.2 | kgCO2e/night | DEFRA 2023 |
| Ground taxi (diesel) | 0.21 | kgCO2e/km | DEFRA 2023 |

---

### 7. `PlantLookup`

SAP plant codes are opaque integers. This table maps them to human-readable facility names per client. In a real deployment, this would be seeded by the client's SAP admin.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `client` | FK → Client | Plant codes are client-specific |
| `plant_code` | VARCHAR(20) | e.g. `1000`, `2000` |
| `facility_name` | VARCHAR(255) | e.g. `"Mumbai HQ"`, `"Pune Factory"` |
| `location` | VARCHAR(255) | Optional — city/region |

---

### 8. `AirportDistance` (Travel source only)

Since Concur/Navan travel exports often only provide IATA airport codes without distances, this lookup table provides great-circle distances between airport pairs. Seeded with distances relevant to the sample data.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `origin_iata` | CHAR(3) | e.g. `BOM` |
| `destination_iata` | CHAR(3) | e.g. `DEL` |
| `distance_km` | INTEGER | Great-circle distance |

**Note:** Bidirectional — `BOM→DEL` and `DEL→BOM` are stored as separate rows since outbound/return may differ slightly due to routing. In a production system this would be replaced with an aviation distance API.

---

## Unit Normalization Logic

### SAP (Scope 1)

```
Diesel in L   → multiply by 2.68  → kgCO2e
Diesel in KG  → divide by 0.85 (density) → get litres → multiply by 2.68
Natural gas M3 → multiply by 2.04
Heating oil L → multiply by 2.52
LPG KG        → multiply by 1.56
```

### Utility (Scope 2)

```
kWh  → multiply by 0.82  → kgCO2e
MWh  → multiply by 1000  → kWh → multiply by 0.82
```

**Billing period alignment:** Utility rows store `billing_period_start` and `billing_period_end` as separate fields in `raw_row`. The `activity_date` on the `EmissionRecord` is set to the billing period start date. Cross-month periods are NOT split — this is a deliberate simplification documented in DECISIONS.md.

### Travel (Scope 3)

```
FLIGHT:       distance_km × cabin_factor × 1 passenger → kgCO2e
              (distance looked up from AirportDistance table if not in source row)
HOTEL:        nights × 31.2 → kgCO2e
GROUND_TAXI:  distance_km × 0.21 → kgCO2e
```

---

## Multi-tenancy Enforcement

Every table that holds client data has a `client` FK. At the Django ORM layer, all querysets are scoped with `.filter(client=request.user.client)` enforced via a base manager. No cross-client query is possible without explicitly bypassing the manager — which is never done in application code.

---

## What This Model Does Not Handle

These are documented in TRADEOFFS.md:

- **Real-time API ingestion** — all ingestion is file-upload based
- **Multi-user roles** — no analyst vs admin distinction, single user type
- **Emission factor versioning UI** — factors are seeded, not editable via the app
