import uuid
from django.db import models
from django.contrib.auth.models import User
from ingestion.models import Client, IngestionBatch


class EmissionFactor(models.Model):
    SCOPE_CHOICES = [('1', 'Scope 1'), ('2', 'Scope 2'), ('3', 'Scope 3')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    material_code = models.CharField(max_length=100, unique=True)
    material_name = models.CharField(max_length=255)
    scope = models.CharField(max_length=1, choices=SCOPE_CHOICES)
    factor_value = models.DecimalField(max_digits=10, decimal_places=6)
    factor_unit = models.CharField(max_length=20)
    source = models.CharField(max_length=255)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.material_name} ({self.factor_value} kgCO2e {self.factor_unit})"


class PlantLookup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    plant_code = models.CharField(max_length=20)
    facility_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ('client', 'plant_code')

    def __str__(self):
        return f"{self.plant_code} → {self.facility_name}"


class AirportDistance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    origin_iata = models.CharField(max_length=3)
    destination_iata = models.CharField(max_length=3)
    distance_km = models.IntegerField()

    class Meta:
        unique_together = ('origin_iata', 'destination_iata')

    def __str__(self):
        return f"{self.origin_iata} → {self.destination_iata}: {self.distance_km}km"


class EmissionRecord(models.Model):
    SOURCE_TYPES = [
        ('SAP', 'SAP'), ('UTILITY', 'Utility'), ('TRAVEL', 'Travel'),
    ]
    SCOPE_CHOICES = [
        ('1', 'Scope 1'), ('2', 'Scope 2'), ('3', 'Scope 3'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('FLAGGED', 'Flagged'),
        ('REJECTED', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='records')
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPES)
    scope = models.CharField(max_length=1, choices=SCOPE_CHOICES)
    activity_date = models.DateField()
    description = models.CharField(max_length=500)
    raw_value = models.DecimalField(max_digits=15, decimal_places=4)
    raw_unit = models.CharField(max_length=20)
    normalized_value = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    normalized_at = models.DateTimeField(null=True, blank=True)
    emission_factor_used = models.ForeignKey(
        EmissionFactor, on_delete=models.SET_NULL, null=True, blank=True
    )
    raw_row = models.JSONField()          # immutable, never update after creation
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    flags = models.JSONField(default=list)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_records'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.source_type} | {self.description} | {self.activity_date}"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('STATUS_CHANGE', 'Status Change'),
        ('VALUE_EDIT', 'Value Edit'),
        ('FLAG_ADDED', 'Flag Added'),
        ('FLAG_REMOVED', 'Flag Removed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.ForeignKey(EmissionRecord, on_delete=models.CASCADE, related_name='audit_logs')
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    field_name = models.CharField(max_length=100)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    comment = models.TextField(blank=True)

    def __str__(self):
        return f"{self.action} on {self.record_id} at {self.changed_at}"