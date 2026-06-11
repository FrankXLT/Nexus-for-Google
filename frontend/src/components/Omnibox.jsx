import React, { useState, useEffect } from 'react';
import useNexusStore from '../store/useNexusStore';
import Icon from './Icon';

const Omnibox = () => {
    const { setSearchQuery, viewMode, setViewMode } = useNexusStore();
    const [inputValue, setInputValue] = useState('');

    useEffect(() => {
        // LAYER 6 INLINE: The Debounce Law—why the setTimeout and cleanup function are used to wait 300ms before dispatching setSearchQuery to protect the backend from API spam.
        // Typing in the Omnibox fires keystrokes rapidly. We use a 300ms setTimeout debounce
        // to prevent spamming the backend API on every keystroke. The cleanup function clears the timer
        // if another keystroke occurs before the 300ms elapses.
        const timer = setTimeout(() => {
            setSearchQuery(inputValue);
        }, 300);
        return () => clearTimeout(timer);
    }, [inputValue, setSearchQuery]);

    return (
        <div className="flex flex-col mb-6 space-y-4">
            <div className="flex items-center bg-bgSurface border border-gray-700 rounded-lg p-2 shadow-inner">
                <Icon name="search_icon" className="w-6 h-6 text-textSecondary mx-2" />
                <input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    placeholder="Search Knowledge Graph or Artifacts..."
                    className="flex-1 bg-transparent text-textPrimary outline-none px-2 placeholder-gray-500"
                />
            </div>
            <div className="flex items-center gap-2">
                <button 
                    onClick={() => setViewMode('STAGING_GRID')}
                    className={`px-4 py-2 text-sm rounded flex items-center gap-2 ${viewMode === 'STAGING_GRID' ? 'bg-accentPrimary text-black font-bold' : 'bg-bgSurface text-textPrimary border border-gray-700 hover:bg-gray-800'}`}>
                    <Icon name="heatmap_icon" className="w-4 h-4" /> Staging Grid
                </button>
                <button 
                    onClick={() => setViewMode('KNOWLEDGE_GRAPH')}
                    className={`px-4 py-2 text-sm rounded flex items-center gap-2 ${viewMode === 'KNOWLEDGE_GRAPH' ? 'bg-accentPrimary text-black font-bold' : 'bg-bgSurface text-textPrimary border border-gray-700 hover:bg-gray-800'}`}>
                    <Icon name="knowledge_graph_icon" className="w-4 h-4" /> Knowledge Graph
                </button>
                <button 
                    onClick={() => setViewMode('TREEMAP')}
                    className={`px-4 py-2 text-sm rounded flex items-center gap-2 ${viewMode === 'TREEMAP' ? 'bg-accentPrimary text-black font-bold' : 'bg-bgSurface text-textPrimary border border-gray-700 hover:bg-gray-800'}`}>
                    <Icon name="treemap_graph_icon" className="w-4 h-4" /> Treemap
                </button>
            </div>
        </div>
    );
};

export default Omnibox;