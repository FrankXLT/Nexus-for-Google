import React, { useEffect, useState } from 'react';
import { Virtuoso } from 'react-virtuoso';
import axios from 'axios';
import useNexusStore from '../store/useNexusStore';
import Icon from './Icon';

const StagingGrid = () => {
    const { artifacts, fetchData, setSelectedArtifact, isLoading, searchScope } = useNexusStore();
    const [selectedIds, setSelectedIds] = useState(new Set());
    const [isQueuing, setIsQueuing] = useState(false);

    useEffect(() => {
        fetchData();
        setSelectedIds(new Set());
    }, [fetchData, searchScope]);

    const handleToggle = (id) => {
        setSelectedIds(prev => {
            const newSet = new Set(prev);
            if (newSet.has(id)) newSet.delete(id);
            else newSet.add(id);
            return newSet;
        });
    };

    const handleEnqueue = async () => {
        if (selectedIds.size === 0) return;
        setIsQueuing(true);
        try {
            await axios.post('/api/proxy/enqueue', {
                source_system: searchScope.toLowerCase(),
                ids: Array.from(selectedIds)
            }, { withCredentials: true });
            
            // Remove queued items from the current view
            const newArtifacts = artifacts.filter(a => !selectedIds.has(a.id));
            useNexusStore.setState({ artifacts: newArtifacts });
            
            setSelectedIds(new Set());
        } catch (e) {
            alert('Failed to enqueue items.');
        } finally {
            setIsQueuing(false);
        }
    };

    if (isLoading && artifacts.length === 0) {
        return <div className="text-textPrimary text-center mt-10">Loading artifacts...</div>;
    }

    const renderRow = (index, artifact) => {
        const isProxy = searchScope !== 'NEXUS';
        return (
            <div className={`flex items-center justify-between p-4 mb-3 bg-bgSurface rounded shadow transition-shadow border ${artifact.state === 'QUARANTINE' ? 'border-red-500' : 'border-gray-800 hover:border-gray-600'}`}>
                <div className="flex items-center gap-4 flex-1 overflow-hidden">
                    {isProxy && (
                        <input 
                            type="checkbox" 
                            checked={selectedIds.has(artifact.id)}
                            onChange={() => handleToggle(artifact.id)}
                            className="w-5 h-5 accent-accentPrimary bg-bgBase border-gray-700 rounded cursor-pointer shrink-0"
                        />
                    )}
                    <div 
                        className={`flex flex-col flex-1 truncate ${!isProxy ? 'cursor-pointer' : ''}`}
                        onClick={() => !isProxy && setSelectedArtifact(artifact)}
                    >
                        <div className="flex items-center gap-2 mb-1">
                            <Icon name={artifact.source_system === 'gmail' ? 'gmail_icon' : 'google_drive_icon'} className="w-4 h-4 shrink-0" />
                            <span className="font-bold text-textPrimary truncate">{artifact.entity_name || artifact.source_sender || 'Unknown Entity'}</span>
                            {artifact.category_name && (
                                <span className="text-xs px-2 py-0.5 rounded-full text-black shrink-0" style={{ backgroundColor: artifact.primary_color_hex || '#e0e0e0' }}>
                                    {artifact.category_name}
                                </span>
                            )}
                            {artifact.nexus_important === 1 && <Icon name="bookmark_filled_icon" className="w-4 h-4 text-accentPrimary shrink-0" />}
                        </div>
                        <div className="text-sm text-textSecondary truncate">{artifact.ui_summary || artifact.snippet || 'No summary available.'}</div>
                        {!isProxy && <div className="text-xs text-gray-500 mt-1 truncate">From: {artifact.source_sender}</div>}
                    </div>
                </div>
                {!isProxy && (
                    <div className="flex items-center shrink-0 ml-4">
                        <span className={`text-xs font-mono uppercase tracking-wide px-3 py-1 border rounded-full ${artifact.state === 'QUARANTINE' ? 'border-red-500 text-red-500' : 'border-gray-700 text-textPrimary'}`}>
                            {artifact.state}
                        </span>
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="h-full w-full flex flex-col relative">
            {searchScope !== 'NEXUS' && artifacts.length > 0 && (
                <div className="mb-4 flex items-center justify-between bg-bgSurface p-3 rounded-lg border border-accentPrimary shrink-0 shadow-[0_0_15px_rgba(187,134,252,0.15)]">
                    <div className="text-sm text-textSecondary">
                        Selected: <span className="font-bold text-white ml-2">{selectedIds.size}</span>
                    </div>
                    <button 
                        onClick={handleEnqueue}
                        disabled={selectedIds.size === 0 || isQueuing}
                        className="px-6 py-2 bg-accentPrimary text-black font-bold rounded disabled:opacity-50 hover:bg-opacity-90 transition-all"
                    >
                        {isQueuing ? 'Queuing...' : 'Add to Nexus Queue'}
                    </button>
                </div>
            )}
            <div className="flex-1 overflow-hidden">
                {artifacts.length > 0 ? (
                    <Virtuoso data={artifacts} itemContent={renderRow} className="h-full w-full pr-2" />
                ) : (
                    <div className="text-textSecondary text-center mt-10">
                        {searchScope === 'NEXUS' ? 'No actionable artifacts found.' : 'Enter a search query to pull live data from Workspace.'}
                    </div>
                )}
            </div>
        </div>
    );
};

export default StagingGrid;
