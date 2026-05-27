# CLAUDE.md — Breathe ESG Project Context

You are helping build a Django REST + React prototype for Breathe ESG, a carbon emissions ingestion and review platform. Read this entire file before writing any code.

---

## What this app does

Ingests emissions data from three CSV sources, normalizes all values to kgCO2e, and surfaces a review dashboard where an analyst can approve/flag/reject rows before they're locked for audit.

The three sources map to GHG Protocol scopes:
- SAP fuel/procurement CSV → Scope 1 (direct emissions)
- Utility electricity CSV → Scope 2 (purchased energy)
- Corporate travel CSV (Concur-style) → Scope 3 (value chain)

**Core principle: raw data and normalized data are never conflated.** Every ingested row stores its original values permanently in `raw_row` (JSONB). Normalization is lazy — it runs when an analyst triggers review, not at ingestion time.

---

## Project structure

```
breathe-esg/
├── core/                  # django config (settings, urls, wsgi)
├── ingestion/             # file upload, parsing, batch tracking
│   ├── parsers/
│   │   ├── sap_parser.py
│   │   ├── utility_parser.py
│   │   └── travel_parser.py
│   ├── models.py          # Client, IngestionBatch, ParseFailure
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── emissions/             # records, normalization, review actions
│   ├── models.py          # EmissionRecord, AuditLog, EmissionFactor, lookups
│   ├── normalizer.py      # all kgCO2e conversion logic lives here
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── docs/
│   ├── MODEL.md           # full data model with rationale
│   ├── DECISIONS.md       # every ambiguity resolved
│   ├── SOURCES.md         # research on each data source
│   └── TRADEOFFS.md       # what was deliberately not built
└── sample_data/
    ├── sap_fuel_procurement.csv
    ├── utility_electricity.csv
    └── corporate_travel.csv
```

---

## Data model (summary — full detail in docs/MODEL.md)

### Tables in `ingestion` app

**Client** — enterprise customer, every data row has a client FK
- id (UUID), name, slug, created_at, is_active

**IngestionBatch** — one per file upload
- id (UUID), client FK, source_type (SAP/UTILITY/TRAVEL), uploaded_by (User FK)
- uploaded_at, original_filename, row_count_total, row_count_success, row_count_failed
- status (PROCESSING/COMPLETE/FAILED), notes

**ParseFailure** — rows that couldn't be parsed, stored for analyst visibility
- id (UUID), batch FK, client FK, row_number, raw_row (JSONField), failure_reason, created_at

### Tables in `emissions` app

**EmissionFactor** — seeded lookup, not editable via UI
- id (UUID), material_code, material_name, scope (1/2/3)
- factor_value (kgCO2e per unit), factor_unit, source, valid_from, valid_to

**PlantLookup** — SAP plant code → facility name, per client
- id (UUID), client FK, plant_code, facility_name, location

**AirportDistance** — IATA pair → great-circle km, for travel normalization
- id (UUID), origin_iata, destination_iata, distance_km

**EmissionRecord** — core table, one per parsed CSV row
- id (UUID), client FK, batch FK
- source_type (SAP/UTILITY/TRAVEL), scope (1/2/3)
- activity_date, description
- raw_value (Decimal), raw_unit (L/KG/M3/kWh/MWh/km/nights)
- normalized_value (Decimal, NULL until normalization runs), normalized_at
- emission_factor_used FK → EmissionFactor
- raw_row (JSONField) — immutable, never updated after creation
- status (PENDING/APPROVED/FLAGGED/REJECTED)
- flags (JSONField) — list of flag codes e.g. ["unit_ambiguous", "outlier", "cabin_class_assumed"]
- reviewed_by (User FK, nullable), reviewed_at (nullable)
- created_at

**AuditLog** — every status change and value edit
- id (UUID), record FK, client FK, changed_by (User FK), changed_at
- action (STATUS_CHANGE/VALUE_EDIT/FLAG_ADDED/FLAG_REMOVED)
- field_name, old_value (text), new_value (text), comment

---

## API endpoints

```
POST   /api/ingestion/upload/          # file upload, source_type in form data
GET    /api/ingestion/batches/         # list all batches
GET    /api/ingestion/batches/:id/     # batch detail + parse failures

GET    /api/emissions/records/         # list records, filter by status/scope/source/date
GET    /api/emissions/records/:id/     # record detail with audit log
PATCH  /api/emissions/records/:id/review/   # {status, comment} — triggers normalization + logs
GET    /api/emissions/records/:id/audit/    # audit log for a record

GET    /api/emissions/factors/         # list emission factors (for UI display)
```

---

## Normalization logic (all lives in emissions/normalizer.py)

### SAP — Scope 1

```python
# Diesel
L  → value * 2.68 = kgCO2e
KG → (value / 0.85) * 2.68 = kgCO2e   # density conversion first

# Heating oil
L  → value * 2.52

# Natural gas
M3 → value * 2.04

# LPG
KG → value * 1.56
```

### Utility — Scope 2

```python
kWh → value * 0.82
MWh → (value * 1000) * 0.82   # convert to kWh first
```

Emission factor source: CEA 2023 (India national grid average)

### Travel — Scope 3

```python
# Flight
distance_km = AirportDistance.lookup(origin, destination)  # or haversine fallback
cabin_factor = 0.255  # economy | 0.765  # business (3x)
kgCO2e = distance_km * cabin_factor

# Hotel
kgCO2e = nights * 31.2

# Ground taxi
kgCO2e = distance_km * 0.21
```

Emission factor source: DEFRA 2023

---

## Parser behavior

Each parser is a standalone class in ingestion/parsers/. It receives a file path and returns:
```python
{
    "records": [...],    # list of dicts ready to create EmissionRecord instances
    "failures": [...],   # list of dicts ready to create ParseFailure instances
}
```

### SAP parser specifics
- Detect encoding: try UTF-8 first, fall back to Windows-1252 (SAP default)
- Date parsing: DD.MM.YYYY format → Python date object
- Header aliases: map German headers to internal names
  - Menge/MENGE → quantity, Meins/MEINS → unit, Bedat/BEDAT → date, etc.
- Unit normalisation happens in normalizer.py, NOT in the parser
- Plant code → facility name via PlantLookup table
- Flag "unit_ambiguous" if material appears with conflicting units in same file

### Utility parser specifics
- Handle both kWh and MWh (flag "unit_mwh_converted" when MWh found)
- activity_date = billing_period_start (do not split cross-month periods)
- Calculate consumption = meter_read_end - meter_read_start if net consumption column missing

### Travel parser specifics
- category column determines record type: FLIGHT / HOTEL / GROUND_TAXI
- Missing cabin_class → default ECONOMY, add flag "cabin_class_assumed"
- Flights: set raw_unit = "km", raw_value = distance from AirportDistance lookup
  - If route not in table, use haversine formula with hardcoded airport coords
- Hotels: raw_unit = "nights", raw_value = nights column
- Ground taxi: raw_unit = "km", raw_value = distance_km column

---

## Key implementation rules

1. **Never modify raw_row after creation.** It is written once at ingestion and never touched.
2. **normalized_value is NULL until review.** Don't normalize at parse time.
3. **Every status change and value edit writes to AuditLog.** No exceptions.
4. **All querysets must be scoped to client.** Use `.filter(client=...)` everywhere. No cross-client data leakage.
5. **Parsers must not crash on bad rows.** Catch per-row exceptions, add to failures list, continue.
6. **Flags are additive.** Never remove a flag during ingestion. Analysts can remove flags via the review action (which gets logged).

---

## Seeded data (run via management command or fixture)

### EmissionFactor seeds
```python
[
  {"material_code": "DIES-001", "material_name": "Diesel", "scope": 1, "factor_value": 2.68, "factor_unit": "per_litre", "source": "DEFRA 2023"},
  {"material_code": "HEIZOEL", "material_name": "Heating Oil", "scope": 1, "factor_value": 2.52, "factor_unit": "per_litre", "source": "DEFRA 2023"},
  {"material_code": "ERGAS-H", "material_name": "Natural Gas", "scope": 1, "factor_value": 2.04, "factor_unit": "per_m3", "source": "DEFRA 2023"},
  {"material_code": "LPG-001", "material_name": "LPG", "scope": 1, "factor_value": 1.56, "factor_unit": "per_kg", "source": "DEFRA 2023"},
  {"material_code": "ELEC-IN", "material_name": "Electricity India Grid", "scope": 2, "factor_value": 0.82, "factor_unit": "per_kwh", "source": "CEA 2023"},
  {"material_code": "FLIGHT-ECO", "material_name": "Flight Economy", "scope": 3, "factor_value": 0.255, "factor_unit": "per_km", "source": "DEFRA 2023"},
  {"material_code": "FLIGHT-BIZ", "material_name": "Flight Business", "scope": 3, "factor_value": 0.765, "factor_unit": "per_km", "source": "DEFRA 2023"},
  {"material_code": "HOTEL", "material_name": "Hotel Night", "scope": 3, "factor_value": 31.2, "factor_unit": "per_night", "source": "DEFRA 2023"},
  {"material_code": "TAXI", "material_name": "Ground Taxi Diesel", "scope": 3, "factor_value": 0.21, "factor_unit": "per_km", "source": "DEFRA 2023"},
]
```

### AirportDistance seeds (routes in sample data)
```python
[
  ("BOM", "DEL", 1150), ("DEL", "BOM", 1150),
  ("BOM", "SIN", 5320), ("SIN", "BOM", 5320),
  ("BOM", "LHR", 7200), ("LHR", "BOM", 7200),
  ("DEL", "BLR", 1740), ("BLR", "DEL", 1740),
  ("BOM", "HYD", 620),  ("HYD", "BOM", 620),
  ("BOM", "MAA", 1030), ("MAA", "BOM", 1030),
  ("DEL", "CCU", 1310), ("CCU", "DEL", 1310),
  ("PNQ", "PNQ", 0),    # ground taxi, same airport
]
```

### PlantLookup seeds (for demo client)
```python
[
  {"plant_code": "1000", "facility_name": "Mumbai HQ", "location": "Mumbai, MH"},
  {"plant_code": "2000", "facility_name": "Pune Factory", "location": "Pune, MH"},
  {"plant_code": "3000", "facility_name": "Delhi Office", "location": "New Delhi"},
  {"plant_code": "4000", "facility_name": "Bangalore R&D", "location": "Bangalore, KA"},
]
```

---

## Tech stack

- **Backend:** Django 4.2, Django REST Framework, PostgreSQL, psycopg2-binary, python-dotenv
- **Frontend:** React (Vite), Axios, TanStack Table, react-dropzone, react-hot-toast
- **Deploy:** Railway (Django + managed PostgreSQL)

---

## What is deliberately NOT built (see docs/TRADEOFFS.md)

1. Real-time API ingestion (SAP OData, Concur API, Green Button XML)
2. Multi-user roles (analyst vs admin vs client portal)
3. Emission factor versioning UI (factors are seeded, not editable in app)

Do not add these. If you think one is needed, flag it with a comment instead of implementing it.

---

## Docs to reference

- `docs/MODEL.md` — full data model with column-level rationale
- `docs/DECISIONS.md` — every ambiguity resolved (ingestion format, scope mapping, billing periods, etc.)
- `docs/SOURCES.md` — research on SAP, utility, and travel data formats
- `docs/TRADEOFFS.md` — what was left out and why
