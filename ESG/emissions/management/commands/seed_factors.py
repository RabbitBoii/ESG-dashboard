from django.core.management.base import BaseCommand
from emissions.models import EmissionFactor, AirportDistance, PlantLookup
from ingestion.models import Client

class Command(BaseCommand):
    def handle(self, *args, **options):
        factors = [
            ("DIES-001", "Diesel", "1", 2.68, "per_litre", "DEFRA 2023"),
            ("HEIZOEL", "Heating Oil", "1", 2.52, "per_litre", "DEFRA 2023"),
            ("ERGAS-H", "Natural Gas", "1", 2.04, "per_m3", "DEFRA 2023"),
            ("LPG-001", "LPG", "1", 1.56, "per_kg", "DEFRA 2023"),
            ("ELEC-IN", "Electricity India Grid", "2", 0.82, "per_kwh", "CEA 2023"),
            ("FLIGHT-ECO", "Flight Economy", "3", 0.255, "per_km", "DEFRA 2023"),
            ("FLIGHT-BIZ", "Flight Business", "3", 0.765, "per_km", "DEFRA 2023"),
            ("HOTEL", "Hotel Night", "3", 31.2, "per_night", "DEFRA 2023"),
            ("TAXI", "Ground Taxi Diesel", "3", 0.21, "per_km", "DEFRA 2023"),
        ]
        for code, name, scope, val, unit, source in factors:
            EmissionFactor.objects.get_or_create(
                material_code=code,
                defaults={"material_name": name, "scope": scope, "factor_value": val, "factor_unit": unit, "source": source}
            )

        routes = [
            ("BOM","DEL",1150),("DEL","BOM",1150),("BOM","SIN",5320),("SIN","BOM",5320),
            ("BOM","LHR",7200),("LHR","BOM",7200),("DEL","BLR",1740),("BLR","DEL",1740),
            ("BOM","HYD",620),("HYD","BOM",620),("BOM","MAA",1030),("MAA","BOM",1030),
            ("DEL","CCU",1310),("CCU","DEL",1310),
        ]
        for o, d, km in routes:
            AirportDistance.objects.get_or_create(origin_iata=o, destination_iata=d, defaults={"distance_km": km})

        client, _ = Client.objects.get_or_create(slug="demo-corp", defaults={"name": "Demo Corp"})
        plants = [("1000","Mumbai HQ","Mumbai, MH"),("2000","Pune Factory","Pune, MH"),("3000","Delhi Office","New Delhi"),("4000","Bangalore R&D","Bangalore, KA")]
        for code, name, loc in plants:
            PlantLookup.objects.get_or_create(client=client, plant_code=code, defaults={"facility_name": name, "location": loc})

        self.stdout.write("Seeded successfully")