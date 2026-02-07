import './Sidebar.css'

interface SidebarProps {
    currentView: string
    onViewChange: (view: any) => void
    pendingCount: number
}

export function Sidebar({ currentView, onViewChange, pendingCount }: SidebarProps) {
    const menuItems = [
        { id: 'dashboard', icon: '📊', label: 'Dashboard' },
        { id: 'jobs', icon: '💼', label: 'Jobs' },
        { id: 'approvals', icon: '✅', label: 'Approvals', badge: pendingCount },
        { id: 'interview', icon: '🎯', label: 'Interview Prep' },
        { id: 'settings', icon: '⚙️', label: 'Settings' },
    ]

    return (
        <aside className="sidebar">
            <div className="sidebar-header">
                <div className="logo">
                    <span className="logo-icon">🚀</span>
                    <span className="logo-text">JobAgent</span>
                </div>
            </div>

            <nav className="sidebar-nav">
                {menuItems.map((item) => (
                    <button
                        key={item.id}
                        className={`nav-item ${currentView === item.id ? 'active' : ''}`}
                        onClick={() => onViewChange(item.id)}
                    >
                        <span className="nav-icon">{item.icon}</span>
                        <span className="nav-label">{item.label}</span>
                        {item.badge && item.badge > 0 && (
                            <span className="nav-badge">{item.badge}</span>
                        )}
                    </button>
                ))}
            </nav>

            <div className="sidebar-footer">
                <div className="status-indicator">
                    <span className="status-dot"></span>
                    <span>System Online</span>
                </div>
            </div>
        </aside>
    )
}
