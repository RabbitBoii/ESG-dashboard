import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import toast from 'react-hot-toast'
import { uploadFile } from '../api'
import type { UploadResult } from '../types'

const SOURCE_TYPES = ['SAP', 'UTILITY', 'TRAVEL'] as const
type SourceType = typeof SOURCE_TYPES[number]

const SOURCE_INFO: Record<SourceType, { label: string; desc: string; color: string }> = {
    SAP: { label: 'SAP Fuel & Procurement', desc: 'Scope 1 — Diesel, heating oil, natural gas', color: '#4d9fff' },
    UTILITY: { label: 'Utility Electricity', desc: 'Scope 2 — kWh/MWh consumption data', color: '#00d084' },
    TRAVEL: { label: 'Corporate Travel', desc: 'Scope 3 — Flights, hotels, ground transport', color: '#ff8c42' },
}

function UploadZone({ sourceType }: { sourceType: SourceType }) {
    const [result, setResult] = useState<UploadResult | null>(null)
    const [loading, setLoading] = useState(false)
    const info = SOURCE_INFO[sourceType]

    const onDrop = useCallback(async (files: File[]) => {
        if (!files[0]) return
        setLoading(true)
        try {
            const { data } = await uploadFile(files[0], sourceType)
            setResult(data)
            toast.success(`${data.rows_ingested} rows ingested successfully`)
        } catch (e) {
            toast.error('Upload failed — check the file format')
        } finally {
            setLoading(false)
        }
    }, [sourceType])

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop, accept: { 'text/csv': ['.csv'] }, maxFiles: 1
    })

    return (
        <div className="bg-[#111] border border-[#222] rounded-lg p-6 flex flex-col gap-4">
            <div>
                <div className="flex items-center gap-2 mb-1">
                    <span className="mono text-[10px] font-semibold px-2 py-0.5 rounded"
                        style={{ color: info.color, background: `${info.color}15` }}>
                        {sourceType}
                    </span>
                    <span className="text-sm font-semibold">{info.label}</span>
                </div>
                <p className="text-xs text-[#666]">{info.desc}</p>
            </div>

            <div {...getRootProps()} className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all duration-150 ${isDragActive
                ? 'border-[#00d084] bg-[rgba(0,208,132,0.05)]'
                : 'border-[#2a2a2a] hover:border-[#444]'
                }`}>
                <input {...getInputProps()} />
                {loading
                    ? <p className="text-sm text-[#666]">Uploading...</p>
                    : isDragActive
                        ? <p className="text-sm text-[#00d084]">Drop it here</p>
                        : <div>
                            <p className="text-sm text-[#666]">Drop CSV here or <span className="text-[#e8e8e8] underline">browse</span></p>
                            <p className="mono text-[10px] text-[#444] mt-1">.csv only</p>
                        </div>
                }
            </div>

            {result && (
                <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded p-4 flex gap-6">
                    <div>
                        <p className="mono text-[10px] text-[#666] uppercase tracking-wider">Ingested</p>
                        <p className="text-2xl font-semibold text-[#00d084]">{result.rows_ingested}</p>
                    </div>
                    <div>
                        <p className="mono text-[10px] text-[#666] uppercase tracking-wider">Failed</p>
                        <p className="text-2xl font-semibold text-[#ff4d4d]">{result.rows_failed}</p>
                    </div>
                    <div>
                        <p className="mono text-[10px] text-[#666] uppercase tracking-wider">Batch ID</p>
                        <p className="mono text-[10px] text-[#444] mt-1 truncate max-w-[180px]">{result.batch_id}</p>
                    </div>
                </div>
            )}
        </div>
    )
}

export default function Upload() {
    return (
        <div className="max-w-3xl">
            <div className="mb-8">
                <h1 className="text-xl font-semibold mb-1">Upload Emissions Data</h1>
                <p className="text-sm text-[#666]">Upload CSV files for each source type. Rows are parsed and queued for analyst review.</p>
            </div>
            <div className="flex flex-col gap-4">
                {SOURCE_TYPES.map(st => <UploadZone key={st} sourceType={st} />)}
            </div>
        </div>
    )
}