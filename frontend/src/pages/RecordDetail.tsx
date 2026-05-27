import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { getRecord, reviewRecord } from '../api'
import type { RecordDetail } from '../types'
import StatusBadge from '../components/StatusBadge'
import FlagBadge from '../components/FlagBadge'

const SOURCE_COLOR: Record<string, string> = {
    SAP: '#4d9fff', UTILITY: '#00d084', TRAVEL: '#ff8c42'
}

export default function RecordDetailPage() {
    const { id } = useParams<{ id: string }>()
    const navigate = useNavigate()
    const [record, setRecord] = useState<RecordDetail | null>(null)
    const [comment, setComment] = useState('')
    const [loading, setLoading] = useState(true)
    const [reviewing, setReviewing] = useState(false)

    useEffect(() => {
        if (!id) return
        getRecord(id).then(({ data }) => setRecord(data)).finally(() => setLoading(false))
    }, [id])

    const handleReview = async (status: string) => {
        if (!id) return
        setReviewing(true)
        try {
            const { data } = await reviewRecord(id, status, comment)
            setRecord(r => r ? { ...r, ...data } : r)
            toast.success(`Record ${status.toLowerCase()}`)
        } catch {
            toast.error('Review failed')
        } finally {
            setReviewing(false)
        }
    }

    if (loading) return <div className="text-[#444] py-12 text-center">Loading...</div>
    if (!record) return <div className="text-[#444] py-12 text-center">Record not found</div>

    const actionButtons = [
        { label: 'Approve', status: 'APPROVED', color: '#00d084', bg: 'rgba(0,208,132,0.1)' },
        { label: 'Flag', status: 'FLAGGED', color: '#ff8c42', bg: 'rgba(255,140,66,0.1)' },
        { label: 'Reject', status: 'REJECTED', color: '#ff4d4d', bg: 'rgba(255,77,77,0.1)' },
    ]

    return (
        <div className="max-w-4xl">
            {/* back */}
            <button onClick={() => navigate('/records')}
                className="mono text-xs text-[#666] hover:text-[#e8e8e8] mb-6 transition-colors">
                ← Back to dashboard
            </button>

            {/* header */}
            <div className="bg-[#111] border border-[#222] rounded-lg p-6 mb-4">
                <div className="flex items-start justify-between mb-4">
                    <div>
                        <div className="flex items-center gap-2 mb-2">
                            <span className="mono text-[10px] font-semibold px-2 py-0.5 rounded"
                                style={{ color: SOURCE_COLOR[record.source_type], background: `${SOURCE_COLOR[record.source_type]}15` }}>
                                {record.source_type}
                            </span>
                            <span className="mono text-[10px] text-[#666]">Scope {record.scope}</span>
                            <StatusBadge status={record.status} />
                        </div>
                        <h1 className="text-base font-semibold">{record.description}</h1>
                        <p className="mono text-xs text-[#666] mt-1">{record.activity_date}</p>
                    </div>
                </div>

                {/* values */}
                <div className="grid grid-cols-3 gap-4 mt-4">
                    <div className="bg-[#0a0a0a] rounded p-4">
                        <p className="mono text-[10px] text-[#666] uppercase tracking-wider mb-1">Raw Value</p>
                        <p className="mono text-lg font-semibold">{Number(record.raw_value).toLocaleString()}</p>
                        <p className="mono text-xs text-[#666]">{record.raw_unit}</p>
                    </div>
                    <div className="bg-[#0a0a0a] rounded p-4">
                        <p className="mono text-[10px] text-[#666] uppercase tracking-wider mb-1">Normalized</p>
                        <p className="mono text-lg font-semibold text-[#00d084]">
                            {record.normalized_value ? Number(record.normalized_value).toFixed(4) : '—'}
                        </p>
                        <p className="mono text-xs text-[#666]">kgCO2e</p>
                    </div>
                    <div className="bg-[#0a0a0a] rounded p-4">
                        <p className="mono text-[10px] text-[#666] uppercase tracking-wider mb-1">Emission Factor</p>
                        <p className="text-sm font-medium">{record.emission_factor ?? '—'}</p>
                        <p className="mono text-xs text-[#666]">DEFRA / CEA 2023</p>
                    </div>
                </div>

                {/* flags */}
                {record.flags.length > 0 && (
                    <div className="mt-4 flex flex-wrap gap-1">
                        {record.flags.map(f => <FlagBadge key={f} flag={f} />)}
                    </div>
                )}
            </div>

            {/* review actions — only show if pending or flagged */}
            {['PENDING', 'FLAGGED'].includes(record.status) && (
                <div className="bg-[#111] border border-[#222] rounded-lg p-6 mb-4">
                    <h2 className="text-sm font-semibold mb-4">Review Action</h2>
                    <textarea
                        value={comment}
                        onChange={e => setComment(e.target.value)}
                        placeholder="Optional comment for audit log..."
                        className="w-full bg-[#0a0a0a] border border-[#2a2a2a] rounded p-3 text-sm text-[#e8e8e8] placeholder-[#444] outline-none focus:border-[#444] resize-none mb-4"
                        rows={2}
                    />
                    <div className="flex gap-3">
                        {actionButtons.map(b => (
                            <button key={b.status}
                                onClick={() => handleReview(b.status)}
                                disabled={reviewing}
                                className="px-5 py-2 rounded text-sm font-semibold transition-all disabled:opacity-50"
                                style={{ color: b.color, background: b.bg }}>
                                {b.label}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* raw row */}
            <div className="bg-[#111] border border-[#222] rounded-lg p-6 mb-4">
                <h2 className="text-sm font-semibold mb-4">Original Source Row</h2>
                <pre className="mono text-xs text-[#666] bg-[#0a0a0a] rounded p-4 overflow-x-auto leading-relaxed">
                    {JSON.stringify(record.raw_row, null, 2)}
                </pre>
            </div>

            {/* audit log */}
            <div className="bg-[#111] border border-[#222] rounded-lg p-6">
                <h2 className="text-sm font-semibold mb-4">Audit Log</h2>
                {record.audit_log.length === 0 ? (
                    <p className="text-xs text-[#444]">No actions yet</p>
                ) : (
                    <div className="flex flex-col gap-2">
                        {record.audit_log.map((l, i) => (
                            <div key={i} className="flex items-start gap-4 text-xs border-b border-[#1a1a1a] pb-2">
                                <span className="mono text-[#444] whitespace-nowrap">{new Date(l.changed_at).toLocaleString()}</span>
                                <span className="mono text-[#ff8c42]">{l.action}</span>
                                <span className="text-[#666]">{l.field}: <span className="text-[#888] line-through">{l.old_value}</span> → <span className="text-[#e8e8e8]">{l.new_value}</span></span>
                                {l.comment && <span className="text-[#666] italic">"{l.comment}"</span>}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}