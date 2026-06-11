import React from 'react';
import Layout from '../components/Layout';
import Omnibox from '../components/Omnibox';
import VQB from '../components/VQB';
import StagingGrid from '../components/StagingGrid';
import ContextModal from '../components/ContextModal';
import useNexusStore from '../store/useNexusStore';

/**
 * Main dashboard view incorporating the Omnibox, VQB, and Staging Grid.
 *
 * Layer Interactions:
 * - Layer 6 (Frontend UI)
 *
 * State Interactions:
 * - Reads viewMode from NexusStore.
 *
 * @returns {JSX.Element}
 */
const Dashboard = () => {
    const { viewMode } = useNexusStore();

    return (
        <Layout>
            <div className="max-w-6xl mx-auto flex flex-col h-full">
                <Omnibox />
                <VQB />
                <div className="flex-1 overflow-hidden">
                    {viewMode === 'STAGING_GRID' && <StagingGrid />}
                    {viewMode === 'KNOWLEDGE_GRAPH' && (
                        <div className="flex items-center justify-center h-full bg-bgSurface border border-gray-800 rounded-lg">
                            <div className="text-center text-textSecondary">
                                <p className="text-lg font-bold mb-2">Knowledge Graph</p>
                                <p>This view will visualize taxonomic linkages.</p>
                            </div>
                        </div>
                    )}
                    {viewMode === 'TREEMAP' && (
                        <div className="flex items-center justify-center h-full bg-bgSurface border border-gray-800 rounded-lg">
                            <div className="text-center text-textSecondary">
                                <p className="text-lg font-bold mb-2">Treemap View</p>
                                <p>This view will visualize density and importance.</p>
                            </div>
                        </div>
                    )}
                </div>
            </div>
            <ContextModal />
        </Layout>
    );
};

export default Dashboard;