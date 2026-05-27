import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from emissions.models import AirportDistance, PlantLookup
from ingestion.models import Client

routes = [
    ("BOM", "DEL", 1150), ("DEL", "BOM", 1150),
    ("BOM", "SIN", 5320), ("SIN", "BOM", 5320),
    ("BOM", "LHR", 7200), ("LHR", "BOM", 7200),
    ("DEL", "BLR", 1740), ("BLR", "DEL", 1740),
    ("BOM", "HYD", 620),  ("HYD", "BOM", 620),
    ("BOM", "MAA", 1030), ("MAA", "BOM", 1030),
    ("DEL", "CCU", 1310), ("CCU", "DEL", 1310),
]

for o, d, km in routes:
    AirportDistance.objects.get_or_create(
        origin_iata=o, destination_iata=d,
        defaults={"distance_km": km}
    )

print(f"Seeded {AirportDistance.objects.count()} airport routes")

client = Client.objects.get(slug="demo-corp")
plants = [
    ("1000", "Mumbai HQ", "Mumbai, MH"),
    ("2000", "Pune Factory", "Pune, MH"),
    ("3000", "Delhi Office", "New Delhi"),
    ("4000", "Bangalore R&D", "Bangalore, KA"),
]

for code, name, loc in plants:
    PlantLookup.objects.get_or_create(
        client=client, plant_code=code,
        defaults={"facility_name": name, "location": loc}
    )

print(f"Seeded {PlantLookup.objects.count()} plant lookups")