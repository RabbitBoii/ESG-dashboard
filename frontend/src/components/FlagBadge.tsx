const FLAG_LABELS: Record<string, string> = {
    cabin_class_assumed: 'cabin assumed',
    distance_estimated_haversine: 'dist. estimated',
    unit_mwh_converted: 'MWh→kWh',
    unit_kg_converted_to_litres: 'KG→L',
    normalization_failed: 'norm. failed',
}

export default function FlagBadge({ flag }: { flag: string }) {
    return (
        <span className="mono inline-block px-1.5 py-0.5 rounded text-[10px] text-[#ff8c42] bg-[rgba(255,140,66,0.08)] border border-[rgba(255,140,66,0.2)] mr-1">
            ⚑ {FLAG_LABELS[flag] ?? flag}
        </span>
    )
}