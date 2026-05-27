# SOURCES.md — Data Source Research

For each of the three sources: what real-world format was researched, what was learned, what the sample data looks like and why, and what would break in a real deployment.

---

## Source 1: SAP — Fuel & Procurement Data

### What was researched

SAP purchasing data lives primarily in two tables: `EKKO` (purchase order header) and `EKPO` (purchase order line items). The standard transaction codes for exporting purchasing reports are:

- **ME2M** — Purchase Orders by Material (most useful for fuel — filter by material group)
- **ME2L** — Purchase Orders by Vendor
- **ME2N** — Purchase Orders by PO Number

Export is done via ALV Grid: run the report → System > List > Save > Local File → choose Text with Tabs or CSV.

Key SAP field names relevant to emissions:
- `EBELN` — Purchase Order number (10-digit)
- `EBELP` — Line item number (5-digit, padded with zeros)
- `BEDAT` — PO date, format `DD.MM.YYYY`
- `WERKS` — Plant code (4-digit integer, client-specific)
- `MATNR` — Material number (18-char, left-padded with zeros internally, displayed without)
- `TXZ01` — Short text / material description (often in German in European SAP configurations)
- `MENGE` — Quantity
- `MEINS` — Base unit of measure (`L`, `KG`, `M3`, `ST` for pieces)
- `NETWR` — Net value
- `WAERS` — Currency key

SAP does not have a single universal CSV structure. The columns exported depend on the ALV layout the user has active — different users in the same company may export different column sets. This is a real ingestion challenge.

German column headers appear when the SAP system language is set to German (DE), which is common in European subsidiaries and in SAP's own default configurations. The same field `MENGE` might appear as `Menge` or `Quantity` depending on the system language.

### What was learned

- The same material (e.g. diesel) can be ordered in different units across plants — one plant may order in litres, another in kilograms. Unit normalisation is mandatory, not optional.
- Plant codes are opaque. `1000` is a number that means nothing without a lookup. In large enterprises, plant `1000` is often the "default" or headquarters plant in SAP's demo data, but real clients use their own numbering.
- Material numbers (`MATNR`) are client-specific. There is no global standard for what `DIES-001` means — each company sets up their own material master.
- Dates in `DD.MM.YYYY` format will break any parser that assumes `MM/DD/YYYY` or ISO 8601. This is a common real-world bug.
- The `EBELP` line item field is always 5 digits padded with zeros (`00010`, `00020`) — this can confuse parsers that interpret it as an integer and drop leading zeros.

### What the sample data looks like and why

`sap_fuel_procurement.csv` — 20 rows, 4 plant codes, 4 material types.

Deliberate messiness included:
- **Mixed units:** Diesel appears in both `L` (litres) and `KG` (kilograms) across different plant/vendor combinations. The parser must detect the unit and apply the appropriate conversion (diesel density: 0.85 kg/L).
- **German material descriptions:** `Dieselkraftstoff` (diesel), `Heizöl` (heating oil), `Flüssiggas` (LPG), `Erdgas` (natural gas). One row uses the English `Diesel` for the same material — reflecting the inconsistency of real SAP data where descriptions are entered manually.
- **European date format:** All dates in `DD.MM.YYYY`.
- **4 plant codes:** `1000`, `2000`, `3000`, `4000` — opaque without the PlantLookup table.
- **EBELP as zero-padded string:** `00010` throughout.

### What would break in a real deployment

1. **ALV layout variation:** The client's SAP user exports with a different column layout than expected. Column `MENGE` might be missing and replaced with `Bestellmenge`. The parser needs a header alias map and must fail gracefully when expected columns are absent.
2. **Material classification:** The client's fuel materials have codes like `10000234` instead of `DIES-001`. Without a material-to-fuel-type mapping provided by the client, we can't determine what emission factor to apply.
3. **Multiple company codes:** Large enterprises have multiple company codes in SAP, each potentially with different currencies, plant numbering, and material master data. The prototype assumes a single company code.
4. **Encoding issues:** SAP exports in Windows-1252 encoding by default, not UTF-8. German characters like `ö`, `ü`, `ä` will corrupt if the parser assumes UTF-8 without specifying encoding.
5. **Thousands separators:** SAP formats numbers as `1.234,56` (European: dot as thousands separator, comma as decimal) — the opposite of the English convention. A naive `float()` parse will fail or silently produce wrong values.

---

## Source 2: Utility — Electricity Data

### What was researched

Enterprise electricity data in India comes primarily from:
- **MSEDCL** (Maharashtra), **TSSPDCL** (Telangana), **BESCOM** (Karnataka), **BRPL/BYPL** (Delhi) — state DISCOMs
- Each DISCOM has a consumer portal where HT (High Tension) commercial/industrial customers can download consumption history as CSV or PDF

In the US, the **Green Button** standard (NAESB REQ.21) provides a standardised XML format for utility data export. Most major US utilities (PG&E, ConEd, ComEd) support it. For India, there is no equivalent standard — each DISCOM has its own portal and export format.

Key concepts learned:
- **HT vs LT consumers:** Industrial clients above ~100kW contracted demand are HT consumers. They have separate tariff structures, ToD (Time of Day) metering, and their billing periods are often irregular.
- **Meter readings vs consumption:** Some portals export start/end meter readings; others export net consumption directly. Both must be handled.
- **Units:** kWh is standard for most meters. Large industrial consumers may see MWh. kVAh appears in some tariff structures but is not used for emissions calculation.
- **Billing period alignment:** DISCOM billing cycles are typically 30 days but rarely align to calendar months. A meter read on Jan 3 produces a bill period of Jan 3 – Feb 1.
- **Multiple meters per site:** A single facility may have multiple meters (different feeders, different blocks). Each has its own account ID and meter ID.

### What was learned

- The billing period misalignment is not an edge case — it is the norm. Every enterprise client will have utility data where billing periods cross month boundaries.
- The unit inconsistency (kWh vs MWh) is also common in real exports — large consumers sometimes see MWh on the bill but the portal CSV uses kWh. These can appear in the same file for the same client across different sites.
- India's grid emission factor is published by the **Central Electricity Authority (CEA)** annually. The 2023 figure for the national grid average is **0.82 kgCO2e/kWh**. Regional factors exist (southern grid is cleaner) but the national average is used here as the conservative default.

### What the sample data looks like and why

`utility_electricity.csv` — 15 rows across 5 meters, 4 sites, Jan–Mar 2024.

Deliberate messiness included:
- **Billing periods crossing months:** e.g. `2024-01-03` to `2024-02-01`. None of the periods align to calendar months.
- **Mixed units:** Row 7 (Pune Factory, Feb billing period) has `MWh` as the unit while every other row has `kWh`. This reflects a real scenario where the portal switches units for large consumers.
- **Multiple meters per site:** Mumbai HQ has two meters (Block A, Block B) with different account IDs and slightly offset billing periods.
- **Indian tariff codes:** `TOD-HT-1` (Time of Day High Tension), `LT-Commercial` (Low Tension Commercial) — realistic MSEDCL/Tata Power tariff classifications.
- **INR currency and realistic Indian billing amounts.**

### What would break in a real deployment

1. **PDF bills:** Some facilities teams only have PDF bills, not portal CSV access. PDF parsing would require OCR with layout detection — fragile and format-specific per utility.
2. **Portal format changes:** DISCOMs update their portal CSV formats without notice. A column rename or reorder breaks the parser silently if it's position-based rather than header-based.
3. **Estimated vs actual reads:** Some billing periods are based on estimated meter reads (utility didn't send a meter reader). These are marked in the bill but rarely in the CSV export. Estimated reads should be flagged.
4. **Solar/DG offset:** Clients with rooftop solar or diesel generators (DG sets) may have net metering — the CSV shows net import, not gross consumption. This understates Scope 2 but inflates Scope 1 if DG consumption isn't separately tracked.
5. **Multiple DISCOMs:** A client with offices across states (Maharashtra + Karnataka + Delhi) will get CSVs from three different DISCOMs with three different column structures. The parser needs per-DISCOM format profiles.

---

## Source 3: Corporate Travel — Flights, Hotels, Ground Transport

### What was researched

The two dominant corporate travel management platforms in enterprise are **Concur** (SAP) and **Navan** (formerly TripActions).

**Concur** exposes:
- A Travel Itinerary API (`GET /travel/trip/v1.1/list`) returning trip details in XML or JSON
- An Expense Report API for claimed expenses
- CSV/Excel export from the Concur reporting module (most commonly used by sustainability teams)

**Navan** exposes:
- A REST API with trip and expense endpoints
- CSV export from the Navan dashboard

Key concepts learned:
- Travel data is split by **category**: flights, hotels, ground transport, rail. Each has a different emission factor and different data fields.
- Flights are identified by origin/destination **IATA airport codes** (3-letter: BOM, DEL, LHR). Distances are not always included — they must be calculated.
- **Cabin class** affects the emission factor significantly. Business class emits approximately 3x economy (DEFRA 2023) due to seat footprint and seat factor calculations. Cabin class is often missing from expense reports (the employee submits the cost, not the booking details).
- **Distance calculation:** The GHG Protocol recommends great-circle distance with a **9% uplift** for routing inefficiency. This can be computed offline using the Haversine formula with airport coordinates.
- Hotels are tracked by number of nights and vendor. The emission factor is per room-night (DEFRA 2023: 31.2 kgCO2e/night for a standard hotel, regardless of location — a simplification).
- Ground transport (taxis, rideshare) typically provides distance in km. The emission factor depends on vehicle type — for corporate Ola/Uber, a diesel sedan (0.21 kgCO2e/km) is the default assumption.

### What the sample data looks like and why

`corporate_travel.csv` — 24 rows, 5 employees, 3 categories (FLIGHT, HOTEL, GROUND_TAXI), Jan–Mar 2024.

Deliberate messiness included:
- **Missing cabin class:** Several flight rows have no `cabin_class` value — the employee booked through expense rather than the travel tool and the data is incomplete. The parser defaults these to ECONOMY and adds a `cabin_class_assumed` flag.
- **No distance on flights:** All flight rows have an empty `distance_km` field. Distance is resolved from the `AirportDistance` lookup table using origin/destination IATA codes.
- **Hotel rows have no origin/destination:** Only `nights` and `vendor` are relevant for hotels. Origin/destination fields are empty — the parser must not try to resolve distances for hotel rows.
- **Mix of domestic and international:** BOM→DEL (1,150 km domestic) vs BOM→LHR (7,200 km international) produces wildly different kgCO2e values — useful for testing outlier detection.
- **Business class flights:** Arjun Mehta's Singapore and London trips are BUSINESS class — 3x the emission factor of economy. These will appear as outliers in the dashboard.
- **Ground taxi with distance:** Ola/Uber corporate rows include `distance_km` directly — no lookup needed.
- **Indian corporate travel context:** INR amounts, Indian carriers (IndiGo, SpiceJet, Air India), Indian city airports (BOM, DEL, BLR, HYD, MAA, CCU, PNQ).

### What would break in a real deployment

1. **Unknown airport codes:** Clients travelling to smaller airports or using non-IATA codes (some Indian regional airports use different codes in booking systems). The distance lookup would fail and the record would need manual distance entry.
2. **Multi-leg flights booked as one:** A BOM→DXB→LHR itinerary might appear as a single booking in Concur with origin BOM and destination LHR. The direct great-circle distance significantly underestimates actual flight distance. A real system needs segment-level data.
3. **Personal vs business travel mixing:** Concur captures all expense claims. An employee who books a personal trip on the corporate card will appear in the export. These must be filtered — but there's no reliable automatic way to distinguish them.
4. **Currency conversion:** International trips are billed in foreign currencies. The `amount` field will be in the transaction currency (USD, GBP, SGD). For emissions purposes currency is irrelevant, but for financial reporting it matters. The prototype stores the original currency and amount without conversion.
5. **Platform fragmentation:** A client using Concur for flights but Ola Corporate for ground transport will have two separate exports with different formats. The parser must handle both, ideally via a unified travel CSV schema the client exports to.
