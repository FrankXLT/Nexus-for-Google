import React, { useEffect } from 'react';
import { Virtuoso } from 'react-virtuoso';
import useNexusStore from '../store/useNexusStore';
import Icon from './Icon';

const StagingGrid = () => {
    const { artifacts, fetchData, setSelectedArtifact, isLoading } = useNexusStore();

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    if (isLoading && artifacts.length === 0) {
        return <div className="text-textPrimary text-center mt-10">Loading artifacts...</div>;
    }

    const renderRow = (index, artifact) => (
        <div 
            onClick={() => setSelectedArtifact(artifact)}
            className={`flex items-center justify-between p-4 mb-3 bg-bgSurface rounded shadow hover:shadow-lg transition-shadow border cursor-pointer ${artifact.state === 'QUARANTINE' ? 'border-red-500' : 'border-gray-800 hover:border-gray-600'}`}>
            <div className="flex flex-col">
                <div className="flex items-center gap-2 mb-1">
                    <Icon name={artifact.source_system === 'gmail' ? 'gmail_icon' : 'google_drive_icon'} className="w-4 h-4" />
                    <span className="font-bold text-textPrimary">{artifact.entity_name || 'Unknown Entity'}</span>
                    <span className="text-xs px-2 py-0.5 rounded-full text-black" style={{ backgroundColor: artifact.primary_color_hex || '#e0e0e0' }}>
                        {artifact.category_name}
                    </span>
                    {artifact.nexus_important === 1 && <Icon name="bookmark_filled_icon" className="w-4 h-4 text-accentPrimary" />}
                </div>
                <div className="text-sm text-textSecondary">{artifact.ui_summary || 'No summary available.'}</div>
                <div className="text-xs text-gray-500 mt-1">From: {artifact.source_sender}</div>
            </div>
            <div className="flex items-center">
                <span className={`text-xs font-mono uppercase tracking-wide px-3 py-1 border rounded-full ${artifact.state === 'QUARANTINE' ? 'border-red-500 text-red-500' : 'border-gray-700 text-textPrimary'}`}>
                    {artifact.state}
                </span>
            </div>
        </div>
    );

    return (
        <div className="h-full w-full">
            {artifacts.length > 0 ? (
                <Virtuoso
                    data={artifacts}
                    itemContent={renderRow}
                    className="h-full w-full pr-2"
                />
            ) : (
                <div className="text-textSecondary text-center mt-10">No actionable artifacts found.</div>
            )}
        </div>
    );
};

export default StagingGrid;