import csv
import io
from datetime import datetime
from emissions.models import EmissionFactor, PlantLookup

# German → internal header aliases
HEADER_ALIASES = {
    'ebeln': 'po_number',
    'ebelp': 'line_item',
    'bedat': 'date',
    'werks': 'plant_code',
    'matnr': 'material_code',
    'txz01': 'description',
    'menge': 'quantity',
    'meins': 'unit',
    'netwr': 'net_value',
    'waers': 'currency',
    # english variants (same SAP fields, english headers)
    'purchasing document': 'po_number',
    'item': 'line_item',
    'document date': 'date',
    'plant': 'plant_code',
    'material': 'material_code',
    'short text': 'description',
    'quantity': 'quantity',
    'order unit': 'unit',
    'net order value': 'net_value',
    'currency': 'currency',
}

MATERIAL_TO_FACTOR_CODE = {
    'dies': 'DIES-001',
    'diesel': 'DIES-001',
    'dieselkraftstoff': 'DIES-001',
    'heizoel': 'HEIZOEL',
    'heizöl': 'HEIZOEL',
    'heating oil': 'HEIZOEL',
    'ergas': 'ERGAS-H',
    'erdgas': 'ERGAS-H',
    'natural gas': 'ERGAS-H',
    'lpg': 'LPG-001',
    'flüssiggas': 'LPG-001',
    'flussiggas': 'LPG-001',
}


def normalize_headers(raw_headers):
    """Map whatever headers came in to our internal names."""
    normalized = {}
    for i, h in enumerate(raw_headers):
        key = h.strip().lower()
        internal = HEADER_ALIASES.get(key, key)
        normalized[internal] = i
    return normalized


def parse_sap_date(date_str):
    """Handle DD.MM.YYYY and YYYY-MM-DD formats."""
    date_str = date_str.strip()
    for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%m/%d/%Y'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date format: {date_str}")


def resolve_material_code(material_code, description):
    """Map SAP material code or description to our EmissionFactor code."""
    # try material code first (e.g. DIES-001 direct match)
    mc = material_code.strip().lower()
    for key, factor_code in MATERIAL_TO_FACTOR_CODE.items():
        if key in mc:
            return factor_code
    # fall back to description
    desc = description.strip().lower()
    for key, factor_code in MATERIAL_TO_FACTOR_CODE.items():
        if key in desc:
            return factor_code
    return None


class SAPParser:
    def __init__(self, client):
        self.client = client

    def parse(self, file_obj):
        records = []
        failures = []

        # try utf-8 first, fall back to windows-1252 (SAP default encoding)
        try:
            content = file_obj.read().decode('utf-8')
        except UnicodeDecodeError:
            file_obj.seek(0)
            content = file_obj.read().decode('windows-1252')

        reader = csv.reader(io.StringIO(content))
        raw_rows = list(reader)

        if not raw_rows:
            return {"records": [], "failures": []}

        headers = normalize_headers(raw_rows[0])
        required = {'date', 'plant_code', 'material_code', 'description', 'quantity', 'unit'}

        for row_num, row in enumerate(raw_rows[1:], start=2):
            raw_dict = {k: (row[v].strip() if v < len(row) else '') for k, v in headers.items()}

            try:
                # check required fields
                missing = [f for f in required if not raw_dict.get(f)]
                if missing:
                    raise ValueError(f"Missing required fields: {', '.join(missing)}")

                activity_date = parse_sap_date(raw_dict['date'])
                quantity = float(raw_dict['quantity'].replace(',', '.'))
                unit = raw_dict['unit'].strip().upper()
                material_code = raw_dict.get('material_code', '')
                description = raw_dict.get('description', '')

                if unit not in ('L', 'KG', 'M3'):
                    raise ValueError(f"Unrecognised unit: {unit}")

                factor_code = resolve_material_code(material_code, description)
                if not factor_code:
                    raise ValueError(f"Cannot map material '{material_code}' / '{description}' to emission factor")

                # look up plant name
                plant_code = raw_dict.get('plant_code', '')
                try:
                    plant = PlantLookup.objects.get(client=self.client, plant_code=plant_code)
                    facility = plant.facility_name
                except PlantLookup.DoesNotExist:
                    facility = f"Plant {plant_code}"

                flags = []
                # flag if diesel appears in both L and KG (checked at batch level later)
                if factor_code == 'DIES-001' and unit == 'KG':
                    flags.append('unit_kg_converted_to_litres')

                records.append({
                    'source_type': 'SAP',
                    'scope': '1',
                    'activity_date': activity_date,
                    'description': f"{description} — {facility}",
                    'raw_value': quantity,
                    'raw_unit': unit,
                    'emission_factor_code': factor_code,
                    'raw_row': raw_dict,
                    'flags': flags,
                })

            except Exception as e:
                failures.append({
                    'row_number': row_num,
                    'raw_row': raw_dict,
                    'failure_reason': str(e),
                })

        return {"records": records, "failures": failures}