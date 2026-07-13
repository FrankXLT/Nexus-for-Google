import React, { useState } from 'react';
import useNexusStore from '../store/useNexusStore';
import Icon from './Icon';

/**
 * Omnibox — the primary search and chip input control for the Dashboard.
 *
 * Layer Interactions:
 * - Layer 6 (Frontend UI): Drives search mode transitions and chip state.
 *
 * State Interactions:
 * - Reads/writes: searchQuery, searchScope, chips, isExploreMode, viewMode from NexusStore.
 * - Calls: executeSearch(), returnToExplore(), addChip(), removeChip(), setSearchScope(), setViewMode().
 *
 * Behavior:
 * - In Explore Mode: shows input + chips only. Search fires on button press.
 * - In Search Mode: shows mode toggle buttons (STAGING_GRID / KNOWLEDGE_GRAPH / TREEMAP).
 *
 * @returns {JSX.Element}
 */
const SCOPE_OPTIONS = [
    { value: 'NEXUS', label: 'Nexus DB', icon: 'knowledge_graph_icon' },
    { value: 'GMAIL', label: 'Proxy: Gmail', icon: 'gmail_icon' },
    { value: 'DRIVE', label: 'Proxy: Drive', icon: 'google_drive_icon' },
];

const Omnibox = () => {
    const {
        searchQuery, setSearchQuery,
        searchScope, setSearchScope,
        chips, removeChip, clearChips,
        isExploreMode,
        viewMode, setViewMode,
        executeSearch, returnToExplore,
    } = useNexusStore();

    const [inputValue, setInputValue] = useState('');

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') handleSearch();
        if (e.key === 'Backspace' && inputValue === '' && chips.length > 0) {
            removeChip(chips.length - 1);
        }
    };

    const handleSearch = () => {
        setSearchQuery(inputValue);
        executeSearch();
    };

    const handleBack = () => {
        setInputValue('');
        clearChips();
        returnToExplore();
    };

    return (
        <div className="flex flex-col gap-3 mb-0">
            {/* Back button in search mode */}
            {!isExploreMode && (
                <button
                    onClick={handleBack}
                    className="flex items-center gap-2 text-sm text-textSecondary hover:text-textPrimary transition-colors self-start"
                >
                    <Icon name="chevron-left" className="w-4 h-4" />
                    <span>Back to Explore</span>
                </button>
            )}

            {/* Main Search Bar */}
            <div
                className="flex items-center gap-0 rounded-xl transition-all"
                style={{
                    background: 'var(--bg-surface)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    boxShadow: '0 2px 12px rgba(0,0,0,0.3)',
                }}
                onFocusCapture={(e) => e.currentTarget.style.borderColor = 'rgba(106,90,169,0.5)'}
                onBlurCapture={(e) => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'}
            >
                {/* Scope Selector */}
                <div className="flex items-center shrink-0 px-3" style={{ borderRight: '1px solid rgba(255,255,255,0.06)' }}>
                    <select
                        value={searchScope}
                        onChange={(e) => setSearchScope(e.target.value)}
                        className="bg-transparent text-sm font-bold outline-none cursor-pointer pr-1"
                        style={{ color: 'var(--accent-primary)' }}
                    >
                        {SCOPE_OPTIONS.map(opt => (
                            <option key={opt.value} value={opt.value} style={{ background: '#1E1E24' }}>
                                {opt.label}
                            </option>
                        ))}
                    </select>
                </div>

                {/* Chips + Input Area */}
                <div className="flex-1 flex items-center flex-wrap gap-1.5 px-3 py-2.5 min-h-[48px]">
                    {/* Active chips */}
                    {chips.map((chip, idx) => (
                        <span
                            key={idx}
                            className="nexus-chip text-white"
                            style={{ background: chip.color || 'var(--accent-primary)' }}
                        >
                            {chip.label}
                            <span className="nexus-chip-remove" onClick={() => removeChip(idx)}>✕</span>
                        </span>
                    ))}

                    {/* Search input */}
                    <input
                        type="text"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={chips.length === 0
                            ? (searchScope === 'NEXUS'
                                ? 'Search Knowledge Base, or click a Sankey node to add a filter...'
                                : searchScope === 'GMAIL'
                                ? 'Search Gmail natively (e.g. smcps.org)...'
                                : 'Search Google Drive...')
                            : 'Add more filters...'}
                        className="flex-1 bg-transparent text-textPrimary outline-none placeholder-muted text-sm min-w-[180px]"
                    />
                </div>

                {/* Search Icon */}
                <div className="px-2">
                    <Icon name="search_icon" className="w-4 h-4 opacity-30" />
                </div>

                {/* Search Button */}
                <button className="search-button rounded-r-xl rounded-l-none mr-0" onClick={handleSearch}>
                    Search
                </button>
            </div>

            {/* Mode Toggles (visible in search mode only) */}
            {!isExploreMode && (
                <div className="flex items-center gap-2 animate-slide-in-down">
                    {searchScope === 'NEXUS' && (
                        <>
                            <button
                                className={`mode-toggle ${viewMode === 'STAGING_GRID' ? 'active' : ''}`}
                                onClick={() => setViewMode('STAGING_GRID')}
                            >
                                <Icon name="heatmap_icon" className="w-4 h-4" />
                                Staging Grid
                            </button>
                            <button
                                className={`mode-toggle ${viewMode === 'KNOWLEDGE_GRAPH' ? 'active' : ''}`}
                                onClick={() => setViewMode('KNOWLEDGE_GRAPH')}
                            >
                                <Icon name="knowledge_graph_icon" className="w-4 h-4" />
                                Knowledge Graph
                            </button>
                            <button
                                className={`mode-toggle ${viewMode === 'TREEMAP' ? 'active' : ''}`}
                                onClick={() => setViewMode('TREEMAP')}
                            >
                                <Icon name="treemap_graph_icon" className="w-4 h-4" />
                                Treemap
                            </button>
                        </>
                    )}
                    {searchScope !== 'NEXUS' && (
                        <button
                            className="mode-toggle active"
                            onClick={() => setViewMode('STAGING_GRID')}
                        >
                            <Icon name="heatmap_icon" className="w-4 h-4" />
                            Staging Grid
                        </button>
                    )}
                    <div className="ml-auto text-xs text-muted font-mono">
                        {chips.length > 0 && `${chips.length} filter${chips.length > 1 ? 's' : ''} active`}
                    </div>
                </div>
            )}
        </div>
    );
};

export default Omnibox;
