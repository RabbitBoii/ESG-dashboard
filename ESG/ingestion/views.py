from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Client, IngestionBatch, ParseFailure
from emissions.models import EmissionRecord, AirportDistance, PlantLookup
from .parsers.sap_parser import SAPParser
from .parsers.utility_parser import UtilityParser
from .parsers.travel_parser import TravelParser


PARSER_MAP = {
    'SAP': SAPParser,
    'UTILITY': UtilityParser,
    'TRAVEL': TravelParser,
}


class UploadView(APIView):
    def post(self, request):
        source_type = request.data.get('source_type', '').upper()
        file = request.FILES.get('file')

        if not file:
            return Response({'error': 'No file provided'}, status=400)
        if source_type not in PARSER_MAP:
            return Response({'error': f'Invalid source_type. Choose from: {list(PARSER_MAP.keys())}'}, status=400)

        # use or create demo client (no auth in prototype)
        client, _ = Client.objects.get_or_create(
            slug='demo-corp',
            defaults={'name': 'Demo Corp'}
        )

        batch = IngestionBatch.objects.create(
            client=client,
            source_type=source_type,
            uploaded_by=None,
            original_filename=file.name,
            status='PROCESSING',
        )

        try:
            ParserClass = PARSER_MAP[source_type]
            result = ParserClass(client).parse(file)

            records_to_create = []
            for r in result['records']:
                records_to_create.append(EmissionRecord(
                    client=client,
                    batch=batch,
                    source_type=r['source_type'],
                    scope=r['scope'],
                    activity_date=r['activity_date'],
                    description=r['description'],
                    raw_value=r['raw_value'],
                    raw_unit=r['raw_unit'],
                    raw_row=r['raw_row'],
                    flags=r.get('flags', []),
                    status='PENDING',
                ))
            EmissionRecord.objects.bulk_create(records_to_create)

            for f in result['failures']:
                ParseFailure.objects.create(
                    batch=batch,
                    client=client,
                    row_number=f['row_number'],
                    raw_row=f['raw_row'],
                    failure_reason=f['failure_reason'],
                )

            batch.row_count_total = len(result['records']) + len(result['failures'])
            batch.row_count_success = len(result['records'])
            batch.row_count_failed = len(result['failures'])
            batch.status = 'COMPLETE'
            batch.save()

            return Response({
                'batch_id': str(batch.id),
                'source_type': source_type,
                'rows_ingested': len(result['records']),
                'rows_failed': len(result['failures']),
                'status': 'COMPLETE',
            }, status=201)

        except Exception as e:
            batch.status = 'FAILED'
            batch.save()
            return Response({'error': str(e)}, status=500)


class BatchListView(APIView):
    def get(self, request):
        client = get_object_or_404(Client, slug='demo-corp')
        batches = IngestionBatch.objects.filter(client=client).order_by('-uploaded_at')
        data = [{
            'id': str(b.id),
            'source_type': b.source_type,
            'filename': b.original_filename,
            'uploaded_at': b.uploaded_at,
            'rows_total': b.row_count_total,
            'rows_success': b.row_count_success,
            'rows_failed': b.row_count_failed,
            'status': b.status,
        } for b in batches]
        return Response(data)


class BatchDetailView(APIView):
    def get(self, request, batch_id):
        client = get_object_or_404(Client, slug='demo-corp')
        batch = get_object_or_404(IngestionBatch, id=batch_id, client=client)
        failures = ParseFailure.objects.filter(batch=batch)
        return Response({
            'id': str(batch.id),
            'source_type': batch.source_type,
            'filename': batch.original_filename,
            'uploaded_at': batch.uploaded_at,
            'rows_total': batch.row_count_total,
            'rows_success': batch.row_count_success,
            'rows_failed': batch.row_count_failed,
            'status': batch.status,
            'failures': [{
                'row_number': f.row_number,
                'raw_row': f.raw_row,
                'reason': f.failure_reason,
            } for f in failures],
        })