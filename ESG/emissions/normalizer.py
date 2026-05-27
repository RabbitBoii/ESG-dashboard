from decimal import Decimal
from django.utils import timezone
from emissions.models import EmissionFactor


def normalize_record(record):
    """
    Takes an EmissionRecord instance with raw_value + raw_unit,
    calculates normalized_value in kgCO2e, saves it.
    Returns (success: bool, error_message: str | None)
    """
    try:
        factor_code = _get_factor_code(record)
        if not factor_code:
            return False, "Cannot determine emission factor code"

        try:
            factor = EmissionFactor.objects.get(material_code=factor_code)
        except EmissionFactor.DoesNotExist:
            return False, f"EmissionFactor not found for code: {factor_code}"

        value = Decimal(str(record.raw_value))
        unit = record.raw_unit.strip().upper()
        source = record.source_type

        kgco2e = _calculate(source, factor, value, unit)
        if kgco2e is None:
            return False, f"Cannot normalize unit '{unit}' for source '{source}'"

        record.normalized_value = kgco2e
        record.normalized_at = timezone.now()
        record.emission_factor_used = factor
        record.save(update_fields=['normalized_value', 'normalized_at', 'emission_factor_used'])
        return True, None

    except Exception as e:
        return False, str(e)


def _get_factor_code(record):
    """Pull factor code from raw_row (set by parser) or derive from source."""
    raw = record.raw_row or {}
    # parsers store emission_factor_code in raw_row during parsing
    # but we stored it separately — check description as fallback
    if record.source_type == 'UTILITY':
        return 'ELEC-IN'
    if record.source_type == 'TRAVEL':
        desc = record.description.lower()
        if 'hotel' in desc:
            return 'HOTEL'
        if 'ground' in desc or 'taxi' in desc:
            return 'TAXI'
        if 'business' in desc:
            return 'FLIGHT-BIZ'
        return 'FLIGHT-ECO'
    # SAP — derive from description
    if record.source_type == 'SAP':
        desc = record.description.lower()
        if 'diesel' in desc or 'dies' in desc or 'kraftstoff' in desc:
            return 'DIES-001'
        if 'heiz' in desc or 'heating oil' in desc:
            return 'HEIZOEL'
        if 'erdgas' in desc or 'ergas' in desc or 'natural gas' in desc:
            return 'ERGAS-H'
        if 'lpg' in desc or 'flüssig' in desc or 'flussig' in desc:
            return 'LPG-001'
    return None


def _calculate(source, factor, value, unit):
    """Core conversion logic. Returns Decimal kgCO2e or None."""
    fv = Decimal(str(factor.factor_value))

    if source == 'SAP':
        if unit == 'L':
            return value * fv
        if unit == 'KG' and factor.material_code == 'DIES-001':
            # diesel density 0.85 kg/L
            litres = value / Decimal('0.85')
            return litres * fv
        if unit == 'KG' and factor.material_code == 'LPG-001':
            return value * fv  # LPG factor is per kg already
        if unit == 'M3':
            return value * fv
        return None

    if source == 'UTILITY':
        if unit == 'KWH':
            return value * fv
        if unit == 'MWH':
            return (value * Decimal('1000')) * fv
        return None

    if source == 'TRAVEL':
        # raw_unit is km (flights/taxi) or nights (hotel)
        return value * fv

    return None