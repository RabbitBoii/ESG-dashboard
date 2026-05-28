import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getRecords } from '../api'
import type { EmissionRecord } from '../types'
import StatusBadge from '../components/StatusBadge'
import FlagBadge from '../components/FlagBadge'

const SOURCES = ['', 'SAP', 'UTILITY', 'TRAVEL']
const SCOPES = ['', '1', '2', '3']
const STATUSES = ['', 'PENDING', 'APPROVED', 'FLAGGED', 'REJECTED']

const SCOPE_LABEL: Record<string, string> = { '1': 'Scope 1', '2': 'Scope 2', '3': 'Scope 3' }
const SOURCE_COLOR: Record<string, string> = {
    SAP: '#4d9fff', UTILITY: '#00d084', TRAVEL: '#ff8c42'
}

export default function Records() {
    const [records, setRecords] = useState<EmissionRecord[]>([])
    const [loading, setLoading] = useState(true)
    const [filters, setFilters] = useState({ source_type: '', scope: '', status: '' })
    const navigate = useNavigate()

    useEffect(() => {
        setLoading(true)
        const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== ''))
        getRecords(params)
            .then(({ data }) => setRecords(data))
            .finally(() => setLoading(false))
    }, [filters])

    const set = (key: string, val: string) => setFilters(f => ({ ...f, [key]: val }))

    const filterSelect = (label: string, key: string, options: string[]) => (
        <div className="flex flex-col gap-1.5">
            <label className="mono text-[10px] text-[#444] uppercase tracking-[0.12em] font-medium">{label}</label>
            <select
                value={filters[key as keyof typeof filters]}
                onChange={e => set(key, e.target.value)}
                className="min-w-[110px] bg-[#161616] border border-[#252525] rounded-md px-3 py-1.5 text-xs text-[#d0d0d0] outline-none cursor-pointer transition-colors duration-150 hover:border-[#333] focus:border-[#3a3a3a] appearance-none"
                style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' fill='none' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%23555' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")`, backgroundRepeat: 'no-repeat', backgroundPosition: 'right 10px center' }}
            >
                {options.map(o => <option key={o} value={o}>{o || 'All'}</option>)}
            </select>
        </div>
    )

    return (
        <div>
            {/* header */}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className="text-xl font-semibold mb-1">Review Dashboard</h1>
                    <p className="text-sm text-[#666]">{records.length} records shown</p>
                </div>
            </div>

            {/* filters */}
            <div className="bg-[#0d0d0d] border border-[#1e1e1e] rounded-lg px-5 py-4 mb-4 flex gap-5 flex-wrap items-end">
                {filterSelect('Source', 'source_type', SOURCES)}
                {filterSelect('Scope', 'scope', SCOPES)}
                {filterSelect('Status', 'status', STATUSES)}
            </div>

            {/* table */}
            <div className="bg-[#111] border border-[#222] rounded-lg overflow-hidden">
                <table className="w-full text-sm border-collapse">
                    <thead>
                        <tr className="border-b border-[#1a1a1a]">
                            {['Date', 'Source', 'Scope', 'Description', 'Raw Value', 'kgCO2e', 'Flags', 'Status'].map(h => (
                                <th key={h} className="mono text-[10px] text-[#666] uppercase tracking-wider text-left px-4 py-3 font-medium">
                                    {h}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {loading ? (
                            <tr><td colSpan={8} className="text-center py-12 text-[#444]">Loading...</td></tr>
                        ) : records.length === 0 ? (
                            <tr><td colSpan={8} className="text-center py-12 text-[#444]">No records found</td></tr>
                        ) : records.map(r => (
                            <tr
                                key={r.id}
                                onClick={() => navigate(`/records/${r.id}`)}
                                className="border-b border-[#1a1a1a] hover:bg-[#161616] cursor-pointer transition-colors"
                            >
                                <td className="mono px-4 py-3 text-xs text-[#888]">{r.activity_date}</td>
                                <td className="px-4 py-3">
                                    <span className="mono text-[10px] font-semibold px-2 py-0.5 rounded"
                                        style={{ color: SOURCE_COLOR[r.source_type], background: `${SOURCE_COLOR[r.source_type]}15` }}>
                                        {r.source_type}
                                    </span>
                                </td>
                                <td className="px-4 py-3 text-xs text-[#666]">{SCOPE_LABEL[r.scope]}</td>
                                <td className="px-4 py-3 text-xs max-w-[280px] truncate">{r.description}</td>
                                <td className="mono px-4 py-3 text-xs text-[#888]">
                                    {Number(r.raw_value).toLocaleString()} {r.raw_unit}
                                </td>
                                <td className="mono px-4 py-3 text-xs text-[#00d084]">
                                    {r.normalized_value ? Number(r.normalized_value).toFixed(2) : '—'}
                                </td>
                                <td className="px-4 py-3">
                                    {r.flags.map(f => <FlagBadge key={f} flag={f} />)}
                                </td>
                                <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    )
}