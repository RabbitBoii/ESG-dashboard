type Status = 'PENDING' | 'APPROVED' | 'FLAGGED' | 'REJECTED'

const config: Record<Status, string> = {
    PENDING: 'text-[#f5c518] bg-[rgba(245,197,24,0.1)]',
    APPROVED: 'text-[#00d084] bg-[rgba(0,208,132,0.1)]',
    FLAGGED: 'text-[#ff8c42] bg-[rgba(255,140,66,0.1)]',
    REJECTED: 'text-[#ff4d4d] bg-[rgba(255,77,77,0.1)]',
}

export default function StatusBadge({ status }: { status: string }) {
    const cls = config[status as Status] ?? config.PENDING
    return (
        <span className={`mono inline-block px-2 py-0.5 rounded text-[10px] font-semibold tracking-wider uppercase ${cls}`}>
            {status}
        </span>
    )
}