import React, { useState, useEffect } from 'react';
import axios from 'axios';
import useNexusStore from '../store/useNexusStore';
import Icon from './Icon';

/**
 * ContextModal — Artifact inspector with Source Context and AI Trace tabs.
 *
 * Layer Interactions:
 * - Layer 6 (Frontend UI): Inspector overlay for selected artifacts.
 *
 * State Interactions:
 * - Reads selectedArtifact from NexusStore.
 * - Calls setSelectedArtifact(null) to close.
 * - Fetches AI_AUDIT_LOGS from /api/data/audit/{artifact_id}.
 *
 * @returns {JSX.Element|null}
 */
const STATE_LABELS = {
    SUB: 'Submitted',
    RAW: 'Raw — Extracting',
    TRIAGE: 'Triage — Routing',
    EVALUATING: 'Evaluating',
    QUARANTINE: 'Quarantined',
    ACTIONABLE: 'Actionable',
    ASSIMILATING: 'Assimilating',
    COMPLETED: 'Completed',
    ERROR: 'Error',
};

const getStateBadgeClass = (state) => {
    const map = {
        QUARANTINE: 'state-badge state-badge-quarantine',
        COMPLETED: 'state-badge state-badge-completed',
        ACTIONABLE: 'state-badge state-badge-actionable',
        TRIAGE: 'state-badge state-badge-triage',
        EVALUATING: 'state-badge state-badge-evaluating',
        ASSIMILATING: 'state-badge state-badge-assimilating',
        ERROR: 'state-badge state-badge-error',
    };
    return map[state] || 'state-badge state-badge-default';
};

const MetaRow = ({ label, value, mono = false }) => (
    <div className="flex items-start justify-between gap-4 py-2.5" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
        <span className="text-xs text-muted uppercase font-bold tracking-wider shrink-0 w-36">{label}</span>
        <span className={`text-sm text-textSecondary text-right ${mono ? 'font-mono' : ''}`}>{value || '—'}</span>
    </div>
);

const ContextModal = () => {
    const { selectedArtifact, setSelectedArtifact } = useNexusStore();
    const [activeTab, setActiveTab] = useState('CONTEXT');
    const [logs, setLogs] = useState([]);
    const [logsLoading, setLogsLoading] = useState(false);

    useEffect(() => {
        if (selectedArtifact && activeTab === 'AI_TRACE') {
            setLogsLoading(true);
            // LAYER 6 INLINE: The AI Trace tab provides Tier 1 UI Decision Tracing to eliminate
            // the "black box" effect of the LLM. By showing the exact JSON inputs and outputs of
            // the LLM execution, users can audit the exact reasoning for any automated taxonomy assignment.
            axios.get(`/api/data/audit/${selectedArtifact.id}`, { withCredentials: true })
                .then(res => setLogs(res.data))
                .catch(err => console.error('Failed to fetch AI audit logs', err))
                .finally(() => setLogsLoading(false));
        }
    }, [selectedArtifact, activeTab]);

    if (!selectedArtifact) return null;

    const handleClose = () => {
        setSelectedArtifact(null);
        setActiveTab('CONTEXT');
        setLogs([]);
    };

    const deepLink = selectedArtifact.source_system === 'gmail'
        ? `https://mail.google.com/mail/u/0/#all/${selectedArtifact.id}`
        : `https://drive.google.com/file/d/${selectedArtifact.id}/view`;

    const accentColor = selectedArtifact.category_color_hex || selectedArtifact.primary_color_hex || 'var(--accent-primary)';

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(8px)' }}
            onClick={(e) => e.target === e.currentTarget && handleClose()}
        >
            <div
                className="w-full max-w-3xl max-h-[85vh] flex flex-col animate-slide-in-down"
                style={{
                    background: 'var(--bg-surface)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: '16px',
                    boxShadow: '0 32px 80px rgba(0,0,0,0.7)',
                    overflow: 'hidden',
                }}
            >
                {/* Header */}
                <div className="flex items-center justify-between p-5 shrink-0" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    <div className="flex items-center gap-3 min-w-0">
                        {/* Category accent dot */}
                        <div className="w-3 h-3 rounded-full shrink-0" style={{ background: accentColor }} />
                        <div className="min-w-0">
                            <div className="flex items-center gap-2">
                                <span className="font-bold text-textPrimary truncate">
                                    {selectedArtifact.entity_name || selectedArtifact.source_sender || 'Unknown'}
                                </span>
                                <span className={getStateBadgeClass(selectedArtifact.state)}>
                                    {selectedArtifact.state}
                                </span>
                            </div>
                            <div className="text-xs text-muted font-mono mt-0.5 truncate">{selectedArtifact.id}</div>
                        </div>
                    </div>
                    <button
                        onClick={handleClose}
                        className="p-2 rounded-lg hover:bg-white hover:bg-opacity-5 transition-colors shrink-0"
                    >
                        <Icon name="close-ellipse" className="w-5 h-5 opacity-50 hover:opacity-100" />
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex shrink-0" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    {['CONTEXT', 'AI_TRACE'].map(tab => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className="flex-1 py-3 text-xs font-bold uppercase tracking-wider transition-colors"
                            style={{
                                color: activeTab === tab ? 'var(--accent-primary)' : '#6b7280',
                                borderBottom: activeTab === tab ? `2px solid var(--accent-primary)` : '2px solid transparent',
                                marginBottom: '-1px',
                            }}
                        >
                            {tab === 'CONTEXT' ? 'Source Context' : 'AI Trace'}
                        </button>
                    ))}
                </div>

                {/* Content */}
                <div className="flex-1 overflow-auto p-5">
                    {/* ── CONTEXT TAB ── */}
                    {activeTab === 'CONTEXT' && (
                        <div>
                            {/* Summary */}
                            {selectedArtifact.ui_summary && (
                                <div className="rounded-xl p-4 mb-5" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)' }}>
                                    <p className="text-xs text-muted uppercase font-bold tracking-wider mb-2">AI Summary</p>
                                    <p className="text-sm text-textSecondary leading-relaxed">{selectedArtifact.ui_summary}</p>
                                </div>
                            )}

                            {/* Metadata table */}
                            <div className="mb-5">
                                <MetaRow label="Category" value={selectedArtifact.category_name} />
                                <MetaRow label="Entity" value={selectedArtifact.entity_name} />
                                <MetaRow label="Purpose" value={selectedArtifact.purpose_name} />
                                <MetaRow label="Source" value={selectedArtifact.source_system?.toUpperCase()} />
                                <MetaRow label="Sender" value={selectedArtifact.source_sender} mono />
                                <MetaRow label="Priority" value={selectedArtifact.priority} />
                                <MetaRow
                                    label="Created"
                                    value={selectedArtifact.created_at_ts
                                        ? new Date(selectedArtifact.created_at_ts * 1000).toLocaleString()
                                        : undefined}
                                />
                            </div>

                            {/* Deep link */}
                            <a
                                href={deepLink}
                                target="_blank"
                                rel="noreferrer"
                                className="flex items-center justify-center gap-2 w-full py-3 rounded-xl font-bold text-sm transition-all"
                                style={{
                                    background: 'var(--accent-primary)',
                                    color: '#000',
                                    boxShadow: '0 4px 16px rgba(106,90,169,0.35)'
                                }}
                            >
                                <Icon name={selectedArtifact.source_system === 'gmail' ? 'gmail_icon' : 'google_drive_icon'} className="w-4 h-4" />
                                Open in Workspace
                                <Icon name="open-external" className="w-3.5 h-3.5" />
                            </a>
                        </div>
                    )}

                    {/* ── AI TRACE TAB ── */}
                    {activeTab === 'AI_TRACE' && (
                        <div>
                            {logsLoading ? (
                                <div className="flex items-center justify-center py-20 opacity-40">
                                    <div className="text-center">
                                        <Icon name="sync-svgrepo-com" className="w-6 h-6 mx-auto mb-2" style={{ animation: 'spin 1.5s linear infinite' }} />
                                        <p className="text-sm text-muted">Decrypting telemetry...</p>
                                    </div>
                                </div>
                            ) : logs.length === 0 ? (
                                <div className="flex items-center justify-center py-20 opacity-40">
                                    <div className="text-center">
                                        <Icon name="google-gemini-logo" className="w-8 h-8 mx-auto mb-3 opacity-30" />
                                        <p className="text-sm text-textSecondary">No AI audit logs found for this artifact.</p>
                                    </div>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {/* Token usage summary bar */}
                                    {logs.length > 0 && (
                                        <div className="flex items-center gap-4 p-3 rounded-lg" style={{ background: 'rgba(250,188,18,0.06)', border: '1px solid rgba(250,188,18,0.15)' }}>
                                            <Icon name="google-gemini-logo" className="w-4 h-4 opacity-60" style={{ filter: 'sepia(1) hue-rotate(20deg) saturate(3)' }} />
                                            <span className="text-xs text-aiSparkle font-semibold">
                                                {logs.length} AI pass{logs.length > 1 ? 'es' : ''} ·{' '}
                                                {logs.reduce((a, l) => a + (l.total_tokens || 0), 0).toLocaleString()} total tokens ·{' '}
                                                {logs.reduce((a, l) => a + (l.execution_ms || 0), 0).toLocaleString()}ms total
                                            </span>
                                        </div>
                                    )}

                                    {logs.map((log, i) => (
                                        <div
                                            key={log.id || i}
                                            className="rounded-xl overflow-hidden"
                                            style={{ border: '1px solid rgba(255,255,255,0.06)' }}
                                        >
                                            {/* Log header */}
                                            <div className="flex items-center justify-between px-4 py-3" style={{ background: 'rgba(255,255,255,0.03)' }}>
                                                <span className="font-bold text-sm" style={{ color: 'var(--accent-primary)' }}>
                                                    {log.prompt_name}
                                                </span>
                                                <div className="flex items-center gap-3">
                                                    <span className="text-xs font-mono text-muted">{(log.total_tokens || 0).toLocaleString()} tokens</span>
                                                    <span className="text-xs font-mono text-muted">{(log.execution_ms || 0).toLocaleString()}ms</span>
                                                </div>
                                            </div>

                                            {/* Request */}
                                            <div className="px-4 pt-3 pb-1">
                                                <p className="text-xs text-muted uppercase font-bold tracking-wider mb-1.5">Request</p>
                                                <pre
                                                    className="text-xs rounded-lg p-3 overflow-auto max-h-48"
                                                    style={{ background: '#0a0a0f', color: '#9ca3af', border: '1px solid rgba(255,255,255,0.04)' }}
                                                >
                                                    <code>{JSON.stringify(log.request_payload, null, 2)}</code>
                                                </pre>
                                            </div>

                                            {/* Response */}
                                            <div className="px-4 pt-2 pb-4">
                                                <p className="text-xs text-muted uppercase font-bold tracking-wider mb-1.5">Response</p>
                                                <pre
                                                    className="text-xs rounded-lg p-3 overflow-auto max-h-48"
                                                    style={{ background: '#0a0a0f', color: '#34d399', border: '1px solid rgba(52,211,153,0.08)' }}
                                                >
                                                    <code>{JSON.stringify(log.response_payload, null, 2)}</code>
                                                </pre>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ContextModal;