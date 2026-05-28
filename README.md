# Breathe ESG — Emissions Ingestion & Review Platform

A Django REST + React prototype that ingests emissions data from three real-world source types, normalizes everything to kgCO2e, and surfaces a review dashboard where analysts can approve, flag, or reject rows before they're locked for audit.

Built as part of the Breathe ESG Tech Intern Assignment.

---

## Screenshots
![img1](./ss1.png)
![img1](./ss2.png)

---

## Live Demo

> **App:** [https://esg-dashboard-production-13b5.up.railway.app/]  
> **API:** [https://esg-dashboard-production-13b5.up.railway.app/api/emissions/records/]

---

## What It Does

- **Ingests** CSV data from 3 source types: SAP fuel/procurement, utility electricity, corporate travel
- **Parses** each format with source-specific logic (German headers, mixed units, IATA airport codes)
- **Normalizes** all values to kgCO2e using DEFRA 2023 / CEA 2023 emission factors — lazily, on analyst review
- **Flags** suspicious rows automatically (missing cabin class, estimated distances, unit conversions)
- **Tracks** every approval, rejection, and edit in a full audit log
- **Surfaces** everything in a clean review dashboard with filters by source, scope, and status

---

## Stack

| Layer | Tech |
|---|---|
| Backend | Django 6.0, Django REST Framework |
| Database | SQLite (local) / PostgreSQL (Railway) |
| Frontend | React + TypeScript, Vite, Tailwind CSS |
| Data table | TanStack Table |
| File upload | react-dropzone |
| Deploy | Railway |

---

## Project Structure

```
ESG/                          ← Django backend
├── core/                     ← Project config (settings, urls)
├── ingestion/                ← File upload, parsing, batch tracking
│   ├── parsers/
│   │   ├── sap_parser.py     ← Handles German headers, DD.MM.YYYY dates, mixed units
│   │   ├── utility_parser.py ← Handles kWh/MWh, cross-month billing periods
│   │   └── travel_parser.py  ← Handles IATA codes, missing cabin class, haversine fallback
│   ├── models.py             ← Client, IngestionBatch, ParseFailure
│   └── views.py              ← Upload + batch endpoints
├── emissions/                ← Records, normalization, review actions
│   ├── models.py             ← EmissionRecord, AuditLog, EmissionFactor, lookups
│   ├── normalizer.py         ← All kgCO2e conversion logic
│   └── views.py              ← Records list, detail, review PATCH
├── sample_data/              ← Realistic sample CSVs for all 3 sources
├── docs/                     ← MODEL.md, DECISIONS.md, SOURCES.md, TRADEOFFS.md
└── seed.py                   ← Seeds EmissionFactor, AirportDistance, PlantLookup

frontend/                     ← React + TypeScript
├── src/
│   ├── api/index.ts          ← All axios calls
│   ├── types/index.ts        ← TypeScript interfaces
│   ├── pages/
│   │   ├── Upload.tsx        ← Drag and drop per source type
│   │   ├── Records.tsx       ← Main review dashboard
│   │   └── RecordDetail.tsx  ← Single record + approve/flag/reject
│   └── components/
│       ├── Navbar.tsx
│       ├── StatusBadge.tsx
│       └── FlagBadge.tsx
```

---

## Data Sources

### SAP — Fuel & Procurement (Scope 1)
Flat file CSV export from SAP ME2M transaction. Handles German column headers (`MENGE`, `MEINS`, `BEDAT`), European date format (`DD.MM.YYYY`), mixed units for the same material (diesel in both `L` and `KG`), and opaque plant codes resolved via a lookup table.

**Emission factors:** Diesel 2.68 kgCO2e/L, Heating Oil 2.52 kgCO2e/L, Natural Gas 2.04 kgCO2e/m³, LPG 1.56 kgCO2e/kg — DEFRA 2023.

### Utility — Electricity (Scope 2)
Portal CSV export (MSEDCL/Tata Power style). Handles billing periods that don't align to calendar months, mixed units (kWh and MWh in the same file), and multiple meters per site.

**Emission factor:** 0.82 kgCO2e/kWh — CEA 2023 India national grid average.

### Corporate Travel (Scope 3)
Concur-style CSV export. Handles flights (IATA airport codes → distance lookup → haversine fallback), hotels (per night), and ground transport (per km). Missing cabin class defaults to Economy with a flag.

**Emission factors:** Flight Economy 0.255, Business 0.765 kgCO2e/km; Hotel 31.2 kgCO2e/night; Taxi 0.21 kgCO2e/km — DEFRA 2023.

---

## API Endpoints

```
POST   /api/ingestion/upload/              Upload CSV file
GET    /api/ingestion/batches/             List all ingestion batches
GET    /api/ingestion/batches/:id/         Batch detail + parse failures

GET    /api/emissions/records/             List records (filter: source_type, scope, status, date)
GET    /api/emissions/records/:id/         Record detail + audit log
PATCH  /api/emissions/records/:id/review/  Approve / Flag / Reject (triggers normalization)
GET    /api/emissions/factors/             List emission factors
```

---

## Key Design Decisions

**Raw data is immutable.** Every ingested row stores its original CSV content in `raw_row` (JSONField) and this field is never modified after creation. Normalization operates on separate fields.

**Normalization is lazy.** `normalized_value` is NULL at ingestion time and calculated when an analyst first reviews the record. This means normalization logic can be updated without re-ingesting source files.

**Scope and source type are independent fields.** SAP=Scope1 is a coincidence of this dataset — in production, SAP procurement data is often Scope 3. Hardcoding the mapping would be a model error.

**Every change is logged.** The AuditLog table records every status change and value edit with old/new values as text — readable by auditors without needing to understand the schema.

See `docs/DECISIONS.md` for the full list of ambiguities resolved.

---

## Running Locally

### Backend

```bash
cd ESG
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
python manage.py migrate
python seed.py              # seeds emission factors, airport distances, plant lookups
python manage.py runserver  # runs at localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                 # runs at localhost:5173
```

### Upload sample data

Use the Upload page at `localhost:5173/upload` or curl:

```bash
curl.exe -X POST http://localhost:8000/api/ingestion/upload/ \
  -F "source_type=SAP" -F "file=@ESG/sample_data/sap_fuel_procurement.csv"

curl.exe -X POST http://localhost:8000/api/ingestion/upload/ \
  -F "source_type=UTILITY" -F "file=@ESG/sample_data/utility_electricity.csv"

curl.exe -X POST http://localhost:8000/api/ingestion/upload/ \
  -F "source_type=TRAVEL" -F "file=@ESG/sample_data/corporate_travel.csv"
```

---

## Docs

| File | Contents |
|---|---|
| `docs/MODEL.md` | Full data model with column-level rationale, normalization logic, multi-tenancy approach |
| `docs/DECISIONS.md` | Every ambiguity resolved — ingestion format, scope mapping, billing periods, airport distances |
| `docs/SOURCES.md` | Research on SAP, utility, and travel data formats + what would break in production |
| `docs/TRADEOFFS.md` | Three things deliberately not built and why |