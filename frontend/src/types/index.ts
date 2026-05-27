export interface EmissionRecord {
    id: string
    source_type: 'SAP' | 'UTILITY' | 'TRAVEL'
    scope: '1' | '2' | '3'
    activity_date: string
    description: string
    raw_value: string
    raw_unit: string
    normalized_value: string | null
    normalized_unit: string
    status: 'PENDING' | 'APPROVED' | 'FLAGGED' | 'REJECTED'
    flags: string[]
    raw_row: Record<string, string>
    batch_id: string
    reviewed_at: string | null
    emission_factor: string | null
}

export interface AuditEntry {
    action: string
    field: string
    old_value: string
    new_value: string
    comment: string
    changed_at: string
}

export interface RecordDetail extends EmissionRecord {
    audit_log: AuditEntry[]
}

export interface Batch {
    id: string
    source_type: string
    filename: string
    uploaded_at: string
    rows_total: number
    rows_success: number
    rows_failed: number
    status: string
}

export interface UploadResult {
    batch_id: string
    source_type: string
    rows_ingested: number
    rows_failed: number
    status: string
}