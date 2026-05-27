import csv
import io
from datetime import datetime


def parse_date(date_str):
    date_str = date_str.strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date format: {date_str}")


class UtilityParser:
    def __init__(self, client):
        self.client = client

    def parse(self, file_obj):
        records = []
        failures = []

        content = file_obj.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))

        for row_num, row in enumerate(reader, start=2):
            raw_dict = {k: v.strip() for k, v in row.items()}

            try:
                # get consumption — direct or calculated from meter reads
                consumption_raw = raw_dict.get('consumption', '').strip()
                if consumption_raw:
                    consumption = float(consumption_raw)
                else:
                    start = float(raw_dict['meter_read_start'])
                    end = float(raw_dict['meter_read_end'])
                    consumption = end - start

                if consumption <= 0:
                    raise ValueError(f"Invalid consumption value: {consumption}")

                unit = raw_dict.get('unit', 'kWh').strip()
                flags = []

                if unit.lower() == 'mwh':
                    consumption = consumption * 1000  # convert to kWh
                    unit = 'kWh'
                    flags.append('unit_mwh_converted')
                elif unit.lower() != 'kwh':
                    raise ValueError(f"Unrecognised unit: {unit}")

                activity_date = parse_date(raw_dict['billing_period_start'])
                site_name = raw_dict.get('site_name', 'Unknown Site')
                meter_id = raw_dict.get('meter_id', '')

                records.append({
                    'source_type': 'UTILITY',
                    'scope': '2',
                    'activity_date': activity_date,
                    'description': f"{site_name} — {meter_id}",
                    'raw_value': consumption,
                    'raw_unit': 'kWh',
                    'emission_factor_code': 'ELEC-IN',
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