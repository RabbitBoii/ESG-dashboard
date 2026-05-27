import csv
import io
import math
from datetime import datetime
from emissions.models import AirportDistance

# hardcoded coords for haversine fallback (lat, lon)
AIRPORT_COORDS = {
    'BOM': (19.0896, 72.8656), 'DEL': (28.5562, 77.1000),
    'BLR': (13.1986, 77.7066), 'HYD': (17.2403, 78.4294),
    'MAA': (12.9941, 80.1709), 'CCU': (22.6542, 88.4467),
    'PNQ': (18.5822, 73.9197), 'SIN': (1.3644, 103.9915),
    'LHR': (51.4700, -0.4543), 'DXB': (25.2532, 55.3657),
}

CABIN_FACTOR_MAP = {
    'ECONOMY': 'FLIGHT-ECO',
    'BUSINESS': 'FLIGHT-BIZ',
    'FIRST': 'FLIGHT-BIZ',   # treat first as business
    '': 'FLIGHT-ECO',        # missing → default economy
}


def haversine(coord1, coord2):
    """Great-circle distance in km between two (lat, lon) pairs."""
    R = 6371
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def get_flight_distance(origin, destination):
    """Look up from DB first, fall back to haversine."""
    try:
        entry = AirportDistance.objects.get(origin_iata=origin, destination_iata=destination)
        return entry.distance_km, False  # (distance, is_estimated)
    except AirportDistance.DoesNotExist:
        pass

    if origin in AIRPORT_COORDS and destination in AIRPORT_COORDS:
        dist = haversine(AIRPORT_COORDS[origin], AIRPORT_COORDS[destination])
        return round(dist), True  # estimated via haversine

    return None, True


def parse_date(date_str):
    date_str = date_str.strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date format: {date_str}")


class TravelParser:
    def __init__(self, client):
        self.client = client

    def parse(self, file_obj):
        records = []
        failures = []

        content = file_obj.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))

        for row_num, row in enumerate(reader, start=2):
            raw_dict = {k: (v.strip() if isinstance(v, str) else str(v)) for k, v in row.items()}

            try:
                category = raw_dict.get('category', '').strip().upper()
                travel_date = parse_date(raw_dict.get('travel_date', ''))
                employee = raw_dict.get('employee_name', 'Unknown')
                department = raw_dict.get('department', '')
                flags = []

                if category == 'FLIGHT':
                    origin = raw_dict.get('origin', '').strip().upper()
                    destination = raw_dict.get('destination', '').strip().upper()
                    cabin = raw_dict.get('cabin_class', '').strip().upper()

                    if not origin or not destination:
                        raise ValueError("Flight row missing origin or destination")

                    distance_km, is_estimated = get_flight_distance(origin, destination)
                    if distance_km is None:
                        raise ValueError(f"Cannot resolve distance for {origin}→{destination}")

                    if is_estimated:
                        flags.append('distance_estimated_haversine')

                    if not cabin:
                        cabin = 'ECONOMY'
                        flags.append('cabin_class_assumed')

                    factor_code = CABIN_FACTOR_MAP.get(cabin, 'FLIGHT-ECO')
                    description = f"Flight {origin}→{destination} ({cabin}) — {employee}"
                    raw_value = distance_km
                    raw_unit = 'km'

                elif category == 'HOTEL':
                    nights_str = raw_dict.get('nights', '').strip()
                    if not nights_str:
                        raise ValueError("Hotel row missing nights")
                    nights = float(nights_str)
                    vendor = raw_dict.get('vendor', 'Unknown Hotel')
                    factor_code = 'HOTEL'
                    description = f"Hotel: {vendor} — {employee}"
                    raw_value = nights
                    raw_unit = 'nights'

                elif category == 'GROUND_TAXI':
                    dist_str = raw_dict.get('distance_km', '').strip()
                    if not dist_str:
                        raise ValueError("Ground taxi row missing distance_km")
                    distance_km = float(dist_str)
                    vendor = raw_dict.get('vendor', 'Taxi')
                    factor_code = 'TAXI'
                    description = f"Ground transport: {vendor} — {employee}"
                    raw_value = distance_km
                    raw_unit = 'km'

                else:
                    raise ValueError(f"Unknown travel category: '{category}'")

                records.append({
                    'source_type': 'TRAVEL',
                    'scope': '3',
                    'activity_date': travel_date,
                    'description': description,
                    'raw_value': raw_value,
                    'raw_unit': raw_unit,
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