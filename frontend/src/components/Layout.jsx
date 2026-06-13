import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Icon from './Icon';
import SystemSettingsModal from './SystemSettingsModal';

/**
 * Core application layout structure with sidebar navigation.
 *
 * Layer Interactions:
 * - Layer 6 (Frontend UI)
 *
 * State Interactions:
 * - Mutates local isSettingsOpen state.
 *
 * @param {Object} props - Child components to render in main area.
 * @returns {JSX.Element}
 */
const Layout = ({ children }) => {
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const navigate = useNavigate();

    return (
        <div className="flex h-screen bg-bgBase overflow-hidden">
            <aside className="w-64 bg-bgSurface border-r border-gray-800 flex flex-col">
                <div className="p-4 flex items-center gap-3 border-b border-gray-800 cursor-pointer" onClick={() => navigate('/')}>
                    <Icon name="google-gemini-logo" className="w-8 h-8" />
                    <span className="font-bold text-textPrimary text-xl tracking-tight">Nexus</span>
                </div>
                <nav className="flex-1 p-4 space-y-2 flex flex-col">
                    <div onClick={() => navigate('/')} className="flex items-center gap-3 p-3 rounded hover:bg-gray-800 text-textPrimary cursor-pointer transition-colors font-medium">
                        <Icon name="heatmap_icon" className="w-5 h-5 text-accentPrimary" />
                        <span>Dashboard</span>
                    </div>
                    <div onClick={() => navigate('/console')} className="flex items-center gap-3 p-3 rounded hover:bg-gray-800 text-textPrimary cursor-pointer transition-colors font-medium">
                        <Icon name="taxonomy_table" className="w-5 h-5 text-accentPrimary" />
                        <span>Taxonomy Matrix</span>
                    </div>
                    
                    <div className="mt-auto">
                        <div className="border-t border-gray-800 my-2"></div>
                        <div onClick={() => setIsSettingsOpen(true)} className="flex items-center gap-3 p-3 rounded hover:bg-gray-800 text-textPrimary cursor-pointer transition-colors font-medium">
                            <Icon name="setting-config" className="w-5 h-5 text-gray-400" />
                            <span>System Settings</span>
                        </div>
                    </div>
                </nav>
            </aside>
            <main className="flex-1 overflow-auto bg-[#0a0a0a]">
                <div className="p-6 h-full">
                    {children}
                </div>
            </main>
            {isSettingsOpen && <SystemSettingsModal onClose={() => setIsSettingsOpen(false)} />}
        </div>
    );
};

export default Layout;