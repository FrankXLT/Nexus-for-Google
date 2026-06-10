import React from 'react';
import useNexusStore from '../store/useNexusStore';
import VQBSankey from './VQBSankey';

const VQB = () => {
    const { artifacts, isLoading } = useNexusStore();

    if (isLoading) {
        return <div className="h-16 flex items-center justify-center text-textSecondary mb-4">Analyzing Context...</div>;
    }

    return (
        <div className="mb-6">
            <h3 className="text-xs text-textSecondary mb-2 font-bold uppercase tracking-wider">Activity Heatmap</h3>
            <div className="grid grid-cols-10 gap-2">
                {artifacts.slice(0, 20).map((artifact) => (
                    <div 
                        key={artifact.id} 
                        className={`h-8 rounded bg-bgSurface ${artifact.state === 'QUARANTINE' ? 'border border-red-500 animate-pulse shadow-[0_0_8px_rgba(239,68,68,0.5)]' : 'border border-gray-800'}`}
                        title={`${artifact.state} - ${artifact.entity_name || 'Unknown'}`}
                    ></div>
                ))}
            </div>
            
            <VQBSankey />
        </div>
    );
};

export default VQB;