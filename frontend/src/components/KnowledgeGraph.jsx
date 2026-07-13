import React, { useEffect } from 'react';
import { Virtuoso } from 'react-virtuoso';
import useNexusStore from '../store/useNexusStore';
import Icon from './Icon';

/**
 * KnowledgeGraph — Fixed-height card grid of processed artifacts.
 *
 * Layer Interactions:
 * - Layer 6 (Frontend UI): Result view for KNOWLEDGE_GRAPH mode.
 *
 * State Interactions:
 * - Reads artifacts, isLoading from NexusStore.
 * - Calls setSelectedArtifact() to open the ContextModal.
 *
 * Rendering:
 * - 3-column fixed-height card grid using Virtuoso for performance.
 * - Each card: category color left-border, entity name, purpose badge, ui_summary.
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

const KnowledgeCard = ({ artifact, onClick }) => {
    const accentColor = artifact.category_color_hex || artifact.primary_color_hex || '#6A5AA9';

    return (
        <div
            className="kg-card animate-fade-in"
            style={{ '--card-accent': accentColor }}
            onClick={() => onClick(artifact)}
        >
            {/* Header */}
            <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex items-center gap-2 min-w-0">
                    <Icon
                        name={artifact.source_system === 'gmail' ? 'gmail_icon' : 'google_drive_icon'}
                        className="w-3.5 h-3.5 shrink-0 opacity-60"
                    />
                    <span className="text-sm font-semibold text-textPrimary truncate">
                        {artifact.entity_name || artifact.source_sender || 'Unknown Entity'}
                    </span>
                </div>
                {artifact.nexus_important === 1 && (
                    <Icon name="bookmark_filled_icon" className="w-3.5 h-3.5 text-accentPrimary shrink-0 mt-0.5" />
                )}
            </div>

            {/* Category + Purpose chips */}
            <div className="flex items-center gap-1.5 mb-2.5 flex-wrap">
                {artifact.category_name && (
                    <span
                        className="text-xs px-2 py-0.5 rounded-full font-semibold text-white shrink-0"
                        style={{ background: accentColor }}
                    >
                        {artifact.category_name}
                    </span>
                )}
                {artifact.purpose_name && (
                    <span
                        className="text-xs px-2 py-0.5 rounded-full font-medium shrink-0"
                        style={{
                            background: 'rgba(255,255,255,0.06)',
                            color: artifact.purpose_color_hex || '#9ca3af',
                            border: `1px solid ${artifact.purpose_color_hex ? artifact.purpose_color_hex + '40' : 'rgba(255,255,255,0.08)'}`
                        }}
                    >
                        {artifact.purpose_name}
                    </span>
                )}
                <span className={`${getStateBadgeClass(artifact.state)} ml-auto`}>
                    {artifact.state}
                </span>
            </div>

            {/* Summary */}
            <p className="text-xs text-textSecondary leading-relaxed line-clamp-3">
                {artifact.ui_summary || artifact.snippet || 'No summary available.'}
            </p>

            {/* Footer */}
            <div className="flex items-center justify-between mt-3 pt-2.5" style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}>
                <span className="text-xs text-muted font-mono truncate max-w-[70%]">
                    {artifact.source_sender || artifact.id}
                </span>
                <Icon name="open-external" className="w-3.5 h-3.5 opacity-20 hover:opacity-60 transition-opacity" />
            </div>
        </div>
    );
};

const KnowledgeGraph = () => {
    const { artifacts, isLoading, setSelectedArtifact } = useNexusStore();

    if (isLoading && artifacts.length === 0) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="text-center">
                    <Icon name="sync-svgrepo-com" className="w-6 h-6 opacity-30 mx-auto mb-3" style={{ animation: 'spin 1.5s linear infinite' }} />
                    <p className="text-sm text-muted">Loading knowledge base...</p>
                </div>
            </div>
        );
    }

    if (artifacts.length === 0) {
        return (
            <div className="flex items-center justify-center h-full opacity-40">
                <div className="text-center">
                    <Icon name="knowledge_graph_icon" className="w-12 h-12 mx-auto mb-3 opacity-30" />
                    <p className="text-sm font-medium text-textSecondary">No results found</p>
                    <p className="text-xs text-muted mt-1">Try a different search or add more data to Nexus.</p>
                </div>
            </div>
        );
    }

    // Group into rows of 3 for Virtuoso
    const rows = [];
    for (let i = 0; i < artifacts.length; i += 3) {
        rows.push(artifacts.slice(i, i + 3));
    }

    return (
        <div className="h-full animate-fade-in">
            <Virtuoso
                data={rows}
                className="h-full"
                itemContent={(_, row) => (
                    <div className="grid grid-cols-3 gap-4 pb-4">
                        {row.map(artifact => (
                            <KnowledgeCard
                                key={artifact.id}
                                artifact={artifact}
                                onClick={setSelectedArtifact}
                            />
                        ))}
                    </div>
                )}
            />
        </div>
    );
};

export default KnowledgeGraph;
