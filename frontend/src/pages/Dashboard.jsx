import React from 'react';
import Layout from '../components/Layout';
import Omnibox from '../components/Omnibox';
import VQB from '../components/VQB';
import StagingGrid from '../components/StagingGrid';
import KnowledgeGraph from '../components/KnowledgeGraph';
import Treemap from '../components/Treemap';
import ContextModal from '../components/ContextModal';
import useNexusStore from '../store/useNexusStore';

/**
 * Dashboard — Main application view.
 *
 * Layer Interactions:
 * - Layer 6 (Frontend UI)
 *
 * State Machine:
 * - isExploreMode = true:  Omnibox at top, VQB fills remaining space.
 * - isExploreMode = false: Omnibox at top (with back button + mode toggles), result view fills space.
 *
 * State Interactions:
 * - Reads isExploreMode, viewMode from NexusStore.
 *
 * @returns {JSX.Element}
 */
const Dashboard = () => {
    const { isExploreMode, viewMode } = useNexusStore();

    return (
        <Layout>
            <div className="flex flex-col h-full" style={{ gap: '16px' }}>
                {/* Omnibox always at top */}
                <Omnibox />

                {/* Explore Mode: VQB fills screen */}
                {isExploreMode && (
                    <VQB />
                )}

                {/* Search Mode: Result views fill screen */}
                {!isExploreMode && (
                    <div className="flex-1 overflow-hidden animate-slide-in-down">
                        {viewMode === 'STAGING_GRID' && <StagingGrid />}
                        {viewMode === 'KNOWLEDGE_GRAPH' && <KnowledgeGraph />}
                        {viewMode === 'TREEMAP' && <Treemap />}
                    </div>
                )}
            </div>

            <ContextModal />
        </Layout>
    );
};

export default Dashboard;