import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import Icon from './Icon';
import SystemSettingsModal from './SystemSettingsModal';

/**
 * Core application layout with sidebar navigation.
 *
 * Layer Interactions:
 * - Layer 6 (Frontend UI)
 *
 * State Interactions:
 * - Reads current route via useLocation for active link highlighting.
 * - Mutates local isSettingsOpen state.
 *
 * @param {Object} props - Child components to render in main area.
 * @returns {JSX.Element}
 */
const Layout = ({ children }) => {
    const [isSettingsOpen, setIsSettingsOpen] = React.useState(false);
    const navigate = useNavigate();
    const location = useLocation();

    const isActive = (path) => location.pathname === path;

    return (
        <div className="flex h-screen bg-bgBase overflow-hidden">
            <aside className="w-60 bg-bgSurface flex flex-col shrink-0" style={{ borderRight: '1px solid rgba(255,255,255,0.06)', boxShadow: '4px 0 24px rgba(0,0,0,0.3)' }}>
                {/* Logo */}
                <div
                    className="h-16 px-5 flex items-center gap-3 cursor-pointer"
                    style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
                    onClick={() => navigate('/')}
                >
                    <Icon name="google-gemini-logo" className="w-7 h-7" />
                    <span className="font-bold text-textPrimary text-lg tracking-tight">Nexus</span>
                    <span className="ml-auto text-xs font-mono text-muted opacity-50">v1.0</span>
                </div>

                {/* Navigation */}
                <nav className="flex-1 p-3 space-y-1">
                    <div
                        className={`sidebar-link ${isActive('/') ? 'active' : ''}`}
                        onClick={() => navigate('/')}
                    >
                        <Icon name="heatmap_icon" className="w-4 h-4 shrink-0" style={{ opacity: isActive('/') ? 1 : 0.5 }} />
                        <span className="text-sm">Dashboard</span>
                    </div>
                    <div
                        className={`sidebar-link ${isActive('/console') ? 'active' : ''}`}
                        onClick={() => navigate('/console')}
                    >
                        <Icon name="taxonomy_table" className="w-4 h-4 shrink-0" style={{ opacity: isActive('/console') ? 1 : 0.5 }} />
                        <span className="text-sm">Taxonomy Matrix</span>
                    </div>
                </nav>

                {/* Bottom Section */}
                <div className="p-3 space-y-1" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                    <div
                        className="sidebar-link"
                        onClick={() => setIsSettingsOpen(true)}
                    >
                        <Icon name="setting-config" className="w-4 h-4 shrink-0 opacity-50" />
                        <span className="text-sm">System Settings</span>
                    </div>
                    {/* User indicator */}
                    <div className="flex items-center gap-3 px-3 py-2 mt-1">
                        <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0"
                            style={{ background: 'linear-gradient(135deg, var(--accent-primary) 0%, #4a3a89 100%)' }}>
                            N
                        </div>
                        <div className="flex-1 min-w-0">
                            <div className="text-xs font-semibold text-textSecondary truncate">Nexus System</div>
                            <div className="text-xs text-muted">Active</div>
                        </div>
                        <div className="w-2 h-2 rounded-full bg-success shrink-0" style={{ boxShadow: '0 0 6px rgba(52,211,153,0.6)' }} />
                    </div>
                </div>
            </aside>

            <main className="flex-1 overflow-auto bg-bgBase">
                <div className="p-6 h-full">
                    {children}
                </div>
            </main>

            {isSettingsOpen && <SystemSettingsModal onClose={() => setIsSettingsOpen(false)} />}
        </div>
    );
};

export default Layout;