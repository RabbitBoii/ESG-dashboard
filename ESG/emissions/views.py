from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ingestion.models import Client
from .models import EmissionRecord, AuditLog, EmissionFactor
from .normalizer import normalize_record


class RecordListView(APIView):
    def get(self, request):
        client = get_object_or_404(Client, slug='demo-corp')
        qs = EmissionRecord.objects.filter(client=client).order_by('-activity_date')

        # filters
        source = request.query_params.get('source_type')
        scope = request.query_params.get('scope')
        status = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        if source:
            qs = qs.filter(source_type=source)
        if scope:
            qs = qs.filter(scope=scope)
        if status:
            qs = qs.filter(status=status)
        if date_from:
            qs = qs.filter(activity_date__gte=date_from)
        if date_to:
            qs = qs.filter(activity_date__lte=date_to)

        data = [_serialize_record(r) for r in qs]
        return Response(data)


class RecordDetailView(APIView):
    def get(self, request, record_id):
        client = get_object_or_404(Client, slug='demo-corp')
        record = get_object_or_404(EmissionRecord, id=record_id, client=client)
        logs = AuditLog.objects.filter(record=record).order_by('changed_at')
        result = _serialize_record(record)
        result['audit_log'] = [{
            'action': l.action,
            'field': l.field_name,
            'old_value': l.old_value,
            'new_value': l.new_value,
            'comment': l.comment,
            'changed_at': l.changed_at,
        } for l in logs]
        return Response(result)


class ReviewRecordView(APIView):
    def patch(self, request, record_id):
        client = get_object_or_404(Client, slug='demo-corp')
        record = get_object_or_404(EmissionRecord, id=record_id, client=client)

        new_status = request.data.get('status', '').upper()
        comment = request.data.get('comment', '')

        if new_status not in ('APPROVED', 'FLAGGED', 'REJECTED'):
            return Response({'error': 'status must be APPROVED, FLAGGED, or REJECTED'}, status=400)

        # normalize lazily on first review if not done yet
        if record.normalized_value is None:
            success, error = normalize_record(record)
            if not success:
                record.flags = record.flags + [f'normalization_failed: {error}']
                record.save(update_fields=['flags'])

        old_status = record.status
        record.status = new_status
        record.reviewed_by = None  # no auth in prototype
        record.reviewed_at = timezone.now()
        record.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])

        # write audit log
        AuditLog.objects.create(
            record=record,
            client=client,
            changed_by=None,
            action='STATUS_CHANGE',
            field_name='status',
            old_value=old_status,
            new_value=new_status,
            comment=comment,
        )

        return Response(_serialize_record(record))


class EmissionFactorListView(APIView):
    def get(self, request):
        factors = EmissionFactor.objects.all().order_by('scope', 'material_name')
        return Response([{
            'code': f.material_code,
            'name': f.material_name,
            'scope': f.scope,
            'factor_value': str(f.factor_value),
            'factor_unit': f.factor_unit,
            'source': f.source,
        } for f in factors])


def _serialize_record(record):
    return {
        'id': str(record.id),
        'source_type': record.source_type,
        'scope': record.scope,
        'activity_date': record.activity_date,
        'description': record.description,
        'raw_value': str(record.raw_value),
        'raw_unit': record.raw_unit,
        'normalized_value': str(record.normalized_value) if record.normalized_value else None,
        'normalized_unit': 'kgCO2e',
        'status': record.status,
        'flags': record.flags,
        'raw_row': record.raw_row,
        'batch_id': str(record.batch_id),
        'reviewed_at': record.reviewed_at,
        'emission_factor': record.emission_factor_used.material_name if record.emission_factor_used else None,
    }