import { Link, useLocation } from 'react-router-dom'

export default function Navbar() {
    const { pathname } = useLocation()

    const links = [
        { to: '/records', label: 'Review Dashboard' },
        { to: '/upload', label: 'Upload Data' },
    ]

    return (
        <nav className="sticky top-0 z-50 bg-[#111] border-b border-[#222] px-6 h-13 flex items-center gap-8">
            <span className="mono text-[#00d084] text-xs font-semibold tracking-widest uppercase">
                Breathe ESG
            </span>
            <div className="flex gap-1">
                {links.map(l => (
                    <Link key={l.to} to={l.to} className={`px-4 py-1.5 rounded text-xs font-medium transition-all duration-150 ${pathname === l.to
                            ? 'text-[#00d084] bg-[rgba(0,208,132,0.08)]'
                            : 'text-[#666] hover:text-[#e8e8e8]'
                        }`}>
                        {l.label}
                    </Link>
                ))}
            </div>
        </nav>
    )
}