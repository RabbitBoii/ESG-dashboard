import { Link, useLocation } from 'react-router-dom'

export default function Navbar() {
    const { pathname } = useLocation()

    const links = [
        { to: '/records', label: 'Review Dashboard' },
        { to: '/upload', label: 'Upload Data' },
    ]

    return (
        <nav className="sticky top-0 z-50 bg-[#0d0d0d] border-b border-[#1e1e1e] px-6 h-14 flex items-center gap-0">
            {/* Logo */}
            <span className="mono text-[#00d084] text-[11px] font-semibold tracking-[0.2em] uppercase select-none">
                Breathe ESG
            </span>

            {/* Divider */}
            <div className="w-px h-4 bg-[#2a2a2a] mx-5" />

            {/* Nav links */}
            <div className="flex items-center gap-1">
                {links.map(l => {
                    const active = pathname === l.to
                    return (
                        <Link
                            key={l.to}
                            to={l.to}
                            className={`relative px-3.5 py-1.5 text-xs font-medium rounded-md transition-all duration-200 ${
                                active
                                    ? 'text-[#00d084] bg-[rgba(0,208,132,0.07)]'
                                    : 'text-[#555] hover:text-[#ccc] hover:bg-[#161616]'
                            }`}
                        >
                            {l.label}
                            {active && (
                                <span className="absolute bottom-0 left-3 right-3 h-px bg-[#00d084] rounded-full opacity-70" />
                            )}
                        </Link>
                    )
                })}
            </div>
        </nav>
    )
}