import uuid
from django.db import models
from django.contrib.auth.models import User


class Client(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class IngestionBatch(models.Model):
    SOURCE_TYPES = [
        ('SAP', 'SAP Fuel & Procurement'),
        ('UTILITY', 'Utility Electricity'),
        ('TRAVEL', 'Corporate Travel'),
    ]
    STATUS_CHOICES = [
        ('PROCESSING', 'Processing'),
        ('COMPLETE', 'Complete'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='batches')
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPES)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    original_filename = models.CharField(max_length=255)
    row_count_total = models.IntegerField(default=0)
    row_count_success = models.IntegerField(default=0)
    row_count_failed = models.IntegerField(default=0)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PROCESSING')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.source_type} — {self.original_filename} ({self.uploaded_at.date()})"


class ParseFailure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='failures')
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    row_number = models.IntegerField()
    raw_row = models.JSONField()
    failure_reason = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Row {self.row_number} — {self.failure_reason}"