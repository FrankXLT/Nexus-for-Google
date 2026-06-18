import React, { useState, useEffect } from 'react';
import useNexusStore from '../store/useNexusStore';
import Icon from './Icon';

const Omnibox = () => {
    const { setSearchQuery, viewMode, setViewMode, searchScope, setSearchScope } = useNexusStore();
    const [inputValue, setInputValue] = useState('');

    useEffect(() => {
        const timer = setTimeout(() => {
            setSearchQuery(inputValue);
        }, 800); // 800ms debounce to protect external APIs
        return () => clearTimeout(timer);
    }, [inputValue, setSearchQuery]);

    return (
        <div className="flex flex-col mb-6 space-y-4">
            <div className="flex items-center bg-bgSurface border border-gray-700 rounded-lg p-2 shadow-inner">
                <select 
                    value={searchScope} 
                    onChange={(e) => setSearchScope(e.target.value)}
                    className="bg-transparent text-accentPrimary outline-none border-r border-gray-700 px-2 mr-2 text-sm font-bold cursor-pointer"
                >
                    <option value="NEXUS">Nexus DB</option>
                    <option value="GMAIL">Proxy: Gmail</option>
                </select>
                <Icon name="search_icon" className="w-6 h-6 text-textSecondary mx-2 shrink-0" />
                <input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    placeholder={searchScope === 'NEXUS' ? "Search Knowledge Graph or Artifacts..." : "Search Gmail natively (e.g. smcps.org)..."}
                    className="flex-1 bg-transparent text-textPrimary outline-none px-2 placeholder-gray-500"
                />
            </div>
            {searchScope === 'NEXUS' && (
                <div className="flex items-center gap-2">
                    <button onClick={() => setViewMode('STAGING_GRID')} className={`px-4 py-2 text-sm rounded flex items-center gap-2 ${viewMode === 'STAGING_GRID' ? 'bg-accentPrimary text-black font-bold' : 'bg-bgSurface text-textPrimary border border-gray-700 hover:bg-gray-800'}`}>
                        <Icon name="heatmap_icon" className="w-4 h-4" /> Staging Grid
                    </button>
                    <button onClick={() => setViewMode('KNOWLEDGE_GRAPH')} className={`px-4 py-2 text-sm rounded flex items-center gap-2 ${viewMode === 'KNOWLEDGE_GRAPH' ? 'bg-accentPrimary text-black font-bold' : 'bg-bgSurface text-textPrimary border border-gray-700 hover:bg-gray-800'}`}>
                        <Icon name="knowledge_graph_icon" className="w-4 h-4" /> Knowledge Graph
                    </button>
                    <button onClick={() => setViewMode('TREEMAP')} className={`px-4 py-2 text-sm rounded flex items-center gap-2 ${viewMode === 'TREEMAP' ? 'bg-accentPrimary text-black font-bold' : 'bg-bgSurface text-textPrimary border border-gray-700 hover:bg-gray-800'}`}>
                        <Icon name="treemap_graph_icon" className="w-4 h-4" /> Treemap
                    </button>
                </div>
            )}
        </div>
    );
};

export default Omnibox;
