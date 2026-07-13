import React, { useEffect } from 'react';
import useNexusStore from '../store/useNexusStore';
import VQBHeatmap from './VQBHeatmap';
import VQBSankey from './VQBSankey';
import Icon from './Icon';

/**
 * VQB (Visual Query Box) — the full-screen exploration panel.
 *
 * Layer Interactions:
 * - Layer 6 (Frontend UI): Wraps the two VQB visualization tabs.
 *
 * State Interactions:
 * - Reads vqbTab, isExploreMode from NexusStore.
 * - Calls setVqbTab(), fetchHeatmap(), fetchSankeyVqb() on mount.
 *
 * Rendering:
 * - Shown only in Explore Mode (isExploreMode === true).
 * - Two tabs: HEATMAP (sender × time) and SANKEY (taxonomy flow).
 * - Wrapped in a nexus-card with a floating offset-header icon.
 * - Full remaining height of the dashboard.
 *
 * @returns {JSX.Element|null}
 */
const VQB = () => {
    const { vqbTab, setVqbTab, isExploreMode, fetchHeatmap, fetchSankeyVqb } = useNexusStore();

    useEffect(() => {
        // Pre-fetch both VQB data sources on mount
        fetchHeatmap(90);
        fetchSankeyVqb();
    }, []);

    if (!isExploreMode) return null;

    return (
        <div
            className="nexus-card flex flex-col overflow-hidden animate-slide-in-down"
            style={{
                flex: '1 1 0',
                minHeight: 0,
                marginTop: '28px',
                paddingTop: '36px',
            }}
        >
            {/* Floating offset header */}
            <div className="offset-header offset-header-accent">
                <Icon name="flow-branch" className="w-5 h-5" style={{ filter: 'brightness(10)' }} />
            </div>

            <div
                className="flex items-center justify-between px-5 pb-3 shrink-0"
                style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}
            >
                <div className="flex items-center gap-2">
                    <span className="text-xs text-muted uppercase tracking-widest font-bold">Explore</span>
                    <div className="w-px h-4 mx-1" style={{ background: 'rgba(255,255,255,0.1)' }} />
                    <button
                        className={`vqb-tab ${vqbTab === 'HEATMAP' ? 'active' : ''}`}
                        onClick={() => setVqbTab('HEATMAP')}
                    >
                        <Icon name="heatmap_icon" className="w-3.5 h-3.5" />
                        Activity Heatmap
                    </button>
                    <button
                        className={`vqb-tab ${vqbTab === 'SANKEY' ? 'active' : ''}`}
                        onClick={() => setVqbTab('SANKEY')}
                    >
                        <Icon name="flow-branch" className="w-3.5 h-3.5" />
                        Taxonomy Flow
                    </button>
                </div>

                <div className="flex items-center gap-2">
                    <span className="text-xs text-muted opacity-50">Last 90 days</span>
                </div>
            </div>

            {/* Tab Content */}
            <div className="flex-1 overflow-hidden p-4">
                {vqbTab === 'HEATMAP' && <VQBHeatmap />}
                {vqbTab === 'SANKEY' && <VQBSankey />}
            </div>
        </div>
    );
};

export default VQB;