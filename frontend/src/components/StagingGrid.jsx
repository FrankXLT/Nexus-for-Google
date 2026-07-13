import React, { useEffect, useState } from 'react';
import { Virtuoso } from 'react-virtuoso';
import axios from 'axios';
import useNexusStore from '../store/useNexusStore';
import Icon from './Icon';

/**
 * StagingGrid — Scrollable artifact list for both Nexus DB and Proxy (Gmail/Drive) modes.
 *
 * Layer Interactions:
 * - Layer 6 (Frontend UI)
 *
 * State Interactions:
 * - Reads artifacts, isLoading, searchScope from NexusStore.
 * - Calls fetchData(), setSelectedArtifact().
 *
 * Behavior:
 * - Nexus mode: Click row → open ContextModal. State badge shown.
 * - Proxy mode: Checkbox rows → bulk enqueue to Nexus.
 * - QUARANTINE rows: Red left border, subtle red tint, glow state badge.
 *
 * @returns {JSX.Element}
 */
const getStateBadgeClass = (state) => {
    switch (state) {
        case 'QUARANTINE': return 'state-badge state-badge-quarantine';
        case 'COMPLETED': return 'state-badge state-badge-completed';
        case 'ACTIONABLE': return 'state-badge state-badge-actionable';
        case 'TRIAGE': return 'state-badge state-badge-triage';
        case 'EVALUATING': return 'state-badge state-badge-evaluating';
        case 'ASSIMILATING': return 'state-badge state-badge-assimilating';
        case 'ERROR': return 'state-badge state-badge-error';
        default: return 'state-badge state-badge-default';
    }
};

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
            const remaining = artifacts.filter(a => !selectedIds.has(a.id));
            useNexusStore.setState({ artifacts: remaining });
            setSelectedIds(new Set());
        } catch {
            alert('Failed to enqueue items.');
        } finally {
            setIsQueuing(false);
        }
    };

    if (isLoading && artifacts.length === 0) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="text-center">
                    <Icon name="sync-svgrepo-com" className="w-6 h-6 opacity-30 mx-auto mb-3" style={{ animation: 'spin 1.5s linear infinite' }} />
                    <p className="text-sm text-muted">Loading artifacts...</p>
                </div>
            </div>
        );
    }

    const isProxy = searchScope !== 'NEXUS';

    const renderRow = (_, artifact) => {
        const isQuarantine = artifact.state === 'QUARANTINE';
        const isChecked = selectedIds.has(artifact.id);
        const accentColor = artifact.category_color_hex || artifact.primary_color_hex;

        return (
            <div
                className={`flex items-center justify-between px-4 py-3 mb-2 rounded-xl transition-all cursor-pointer ${isQuarantine ? 'row-quarantine' : ''}`}
                style={{
                    background: isChecked
                        ? 'rgba(106,90,169,0.08)'
                        : isQuarantine
                        ? 'rgba(239,68,68,0.04)'
                        : 'var(--bg-surface)',
                    border: isChecked
                        ? '1px solid rgba(106,90,169,0.4)'
                        : isQuarantine
                        ? '1px solid rgba(239,68,68,0.3)'
                        : '1px solid rgba(255,255,255,0.05)',
                    boxShadow: isChecked ? '0 0 12px rgba(106,90,169,0.15)' : undefined,
                }}
                onClick={() => {
                    if (isProxy) handleToggle(artifact.id);
                    else setSelectedArtifact(artifact);
                }}
            >
                <div className="flex items-center gap-3 flex-1 overflow-hidden">
                    {isProxy && (
                        <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => handleToggle(artifact.id)}
                            onClick={e => e.stopPropagation()}
                            className="w-4 h-4 rounded cursor-pointer shrink-0"
                            style={{ accentColor: 'var(--accent-primary)' }}
                        />
                    )}

                    {/* Category color dot */}
                    {accentColor && (
                        <div
                            className="w-2.5 h-2.5 rounded-full shrink-0"
                            style={{ background: accentColor }}
                        />
                    )}

                    <div className="flex-1 min-w-0">
                        {/* Top row */}
                        <div className="flex items-center gap-2 mb-0.5">
                            <Icon
                                name={artifact.source_system === 'gmail' ? 'gmail_icon' : 'google_drive_icon'}
                                className="w-3.5 h-3.5 opacity-50 shrink-0"
                            />
                            <span className="font-semibold text-sm text-textPrimary truncate">
                                {artifact.entity_name || artifact.source_sender || 'Unknown Entity'}
                            </span>
                            {artifact.category_name && (
                                <span
                                    className="text-xs px-2 py-0.5 rounded-full text-white font-semibold shrink-0"
                                    style={{ background: accentColor || 'rgba(106,90,169,0.6)' }}
                                >
                                    {artifact.category_name}
                                </span>
                            )}
                            {artifact.nexus_important === 1 && (
                                <Icon name="bookmark_filled_icon" className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--accent-primary)' }} />
                            )}
                        </div>

                        {/* Summary */}
                        <div className="text-xs text-textSecondary truncate">
                            {artifact.ui_summary || artifact.snippet || 'No summary available.'}
                        </div>

                        {/* Sender */}
                        {!isProxy && (
                            <div className="text-xs text-muted mt-0.5 truncate font-mono">
                                {artifact.source_sender}
                            </div>
                        )}
                    </div>
                </div>

                {/* State badge */}
                {!isProxy ? (
                    <div className="shrink-0 ml-4">
                        <span className={getStateBadgeClass(artifact.state)}>
                            {artifact.state}
                        </span>
                    </div>
                ) : (
                    <div className="shrink-0 ml-4">
                        <span className="state-badge state-badge-default">
                            PROXY
                        </span>
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="h-full flex flex-col">
            {/* Proxy enqueue bar */}
            {isProxy && artifacts.length > 0 && (
                <div
                    className="mb-4 flex items-center justify-between p-3 rounded-xl shrink-0"
                    style={{
                        background: 'var(--bg-surface)',
                        border: '1px solid rgba(106,90,169,0.3)',
                        boxShadow: '0 0 20px rgba(106,90,169,0.1)'
                    }}
                >
                    <span className="text-sm text-textSecondary">
                        Selected: <span className="font-bold text-textPrimary ml-1">{selectedIds.size}</span>
                    </span>
                    <button
                        onClick={handleEnqueue}
                        disabled={selectedIds.size === 0 || isQueuing}
                        className="px-5 py-2 font-bold text-sm rounded-lg disabled:opacity-40 transition-all"
                        style={{
                            background: 'var(--accent-primary)',
                            color: '#000',
                            boxShadow: '0 4px 14px rgba(106,90,169,0.35)'
                        }}
                    >
                        {isQueuing ? 'Queuing...' : 'Add to Nexus Queue'}
                    </button>
                </div>
            )}

            {/* Result list */}
            <div className="flex-1 overflow-hidden">
                {artifacts.length > 0 ? (
                    <Virtuoso
                        data={artifacts}
                        itemContent={renderRow}
                        className="h-full"
                    />
                ) : (
                    <div className="flex items-center justify-center h-full opacity-40">
                        <div className="text-center">
                            <Icon name="heatmap_icon" className="w-10 h-10 mx-auto mb-3 opacity-30" />
                            <p className="text-sm font-medium text-textSecondary">
                                {searchScope === 'NEXUS'
                                    ? 'No artifacts found.'
                                    : 'Enter a search query to pull live data from Workspace.'}
                            </p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default StagingGrid;
