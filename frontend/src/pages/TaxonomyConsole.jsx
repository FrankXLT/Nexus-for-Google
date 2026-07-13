import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Virtuoso } from 'react-virtuoso';
import Layout from '../components/Layout';
import Icon from '../components/Icon';

/**
 * TaxonomyConsole — Matrix view for reviewing and approving taxonomy linkages.
 *
 * Layer Interactions:
 * - Layer 6 (Frontend UI)
 *
 * State Interactions:
 * - Reads TAXONOMY_LINKAGES via /api/taxonomy/linkages.
 * - Calls /api/taxonomy/approve/{linkage_id} to transition QUARANTINE → ACTIVE.
 *
 * Rendering:
 * - QUARANTINE rows: Red left border, red tint, glow badge, Approve button.
 * - ACTIVE rows: Green state badge.
 * - Per-column color dots from taxonomy color_hex values.
 *
 * @returns {JSX.Element}
 */
const TaxonomyConsole = () => {
    const [linkages, setLinkages] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState('ALL'); // 'ALL' | 'QUARANTINE' | 'ACTIVE'

    const fetchLinkages = () => {
        setLoading(true);
        axios.get('/api/taxonomy/linkages?limit=500&offset=0', { withCredentials: true })
            .then(res => { setLinkages(res.data); setLoading(false); })
            .catch(err => { console.error(err); setLoading(false); });
    };

    useEffect(() => { fetchLinkages(); }, []);

    const handleApprove = (linkageId) => {
        axios.patch(`/api/taxonomy/approve/${linkageId}`, {}, { withCredentials: true })
            .then(() => fetchLinkages())
            .catch(err => console.error(err));
    };

    const filtered = filter === 'ALL'
        ? linkages
        : linkages.filter(l => l.nexus_state === filter);

    const quarantineCount = linkages.filter(l => l.nexus_state === 'QUARANTINE').length;

    const renderRow = (_, link) => {
        const isQuarantine = link.nexus_state === 'QUARANTINE';

        return (
            <div
                className={`flex items-center justify-between px-4 py-3 mb-2 rounded-xl transition-all ${isQuarantine ? 'row-quarantine' : ''}`}
                style={{
                    background: isQuarantine ? 'rgba(239,68,68,0.04)' : 'var(--bg-surface)',
                    border: isQuarantine
                        ? '1px solid rgba(239,68,68,0.25)'
                        : '1px solid rgba(255,255,255,0.05)',
                }}
            >
                <div className="flex items-center gap-5 flex-1 min-w-0">
                    {/* Category */}
                    <div className="flex items-center gap-2 w-36 shrink-0">
                        {link.category_color_hex && (
                            <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: link.category_color_hex }} />
                        )}
                        <span className="text-sm font-bold text-textPrimary truncate">{link.category_name || '—'}</span>
                    </div>

                    {/* Entity */}
                    <div className="flex items-center gap-2 w-48 shrink-0">
                        {link.entity_color_hex && (
                            <div className="w-2 h-2 rounded-full shrink-0" style={{ background: link.entity_color_hex, opacity: 0.7 }} />
                        )}
                        <span className="text-sm text-textSecondary truncate">{link.entity_name || '—'}</span>
                    </div>

                    {/* Purpose */}
                    <div className="flex items-center gap-2 w-36 shrink-0">
                        <span
                            className="text-xs px-2 py-0.5 rounded-full font-medium"
                            style={{
                                background: link.purpose_color_hex ? link.purpose_color_hex + '22' : 'rgba(255,255,255,0.05)',
                                color: link.purpose_color_hex || '#9ca3af',
                                border: `1px solid ${link.purpose_color_hex ? link.purpose_color_hex + '40' : 'rgba(255,255,255,0.08)'}`,
                            }}
                        >
                            {link.purpose_name || '—'}
                        </span>
                    </div>

                    {/* State badge */}
                    <span className={`state-badge ${isQuarantine ? 'state-badge-quarantine' : 'state-badge-completed'}`}>
                        {link.nexus_state}
                    </span>
                </div>

                <div className="flex items-center gap-3 shrink-0 ml-4">
                    <span className="text-xs text-muted font-mono opacity-50">
                        {link.last_active_ts ? new Date(link.last_active_ts * 1000).toLocaleDateString() : '—'}
                    </span>
                    {isQuarantine && (
                        <button
                            onClick={() => handleApprove(link.linkage_id)}
                            className="px-4 py-1.5 text-sm font-bold rounded-lg transition-all"
                            style={{
                                background: 'var(--accent-primary)',
                                color: '#000',
                                boxShadow: '0 0 14px rgba(106,90,169,0.3)'
                            }}
                        >
                            Approve
                        </button>
                    )}
                </div>
            </div>
        );
    };

    return (
        <Layout>
            <div className="h-full flex flex-col" style={{ gap: '20px' }}>
                {/* Header */}
                <div className="nexus-card p-5 pt-10 relative shrink-0">
                    <div className="offset-header offset-header-accent">
                        <Icon name="taxonomy_flow_icon" className="w-5 h-5" style={{ filter: 'brightness(10)' }} />
                    </div>
                    <div className="flex items-center justify-between ml-12">
                        <div>
                            <h1 className="text-xl font-bold text-textPrimary">Taxonomy Matrix</h1>
                            <p className="text-sm text-textSecondary mt-0.5">
                                Manage active mappings and approve quarantined entities.
                            </p>
                        </div>
                        <div className="flex items-center gap-3">
                            {quarantineCount > 0 && (
                                <span className="state-badge state-badge-quarantine">
                                    {quarantineCount} Quarantined
                                </span>
                            )}
                            <div className="flex items-center gap-1 rounded-lg p-1" style={{ background: 'var(--bg-base)' }}>
                                {['ALL', 'QUARANTINE', 'ACTIVE'].map(f => (
                                    <button
                                        key={f}
                                        onClick={() => setFilter(f)}
                                        className="px-3 py-1.5 text-xs font-semibold rounded-md transition-all"
                                        style={{
                                            background: filter === f ? 'var(--bg-surface)' : 'transparent',
                                            color: filter === f ? '#fff' : '#6b7280',
                                        }}
                                    >
                                        {f}
                                    </button>
                                ))}
                            </div>
                            <button onClick={fetchLinkages} className="p-2 rounded-lg hover:bg-white hover:bg-opacity-5 transition-colors">
                                <Icon name="sync-svgrepo-com" className="w-4 h-4 opacity-50" />
                            </button>
                        </div>
                    </div>
                </div>

                {/* Column headers */}
                <div className="flex items-center px-4 gap-5 shrink-0">
                    <span className="text-xs text-muted uppercase font-bold tracking-wider w-36">Category</span>
                    <span className="text-xs text-muted uppercase font-bold tracking-wider w-48">Entity</span>
                    <span className="text-xs text-muted uppercase font-bold tracking-wider w-36">Purpose</span>
                    <span className="text-xs text-muted uppercase font-bold tracking-wider">State</span>
                    <span className="text-xs text-muted uppercase font-bold tracking-wider ml-auto">Last Active</span>
                </div>

                {/* Rows */}
                <div className="flex-1 overflow-hidden">
                    {loading ? (
                        <div className="flex items-center justify-center h-full opacity-40">
                            <div className="text-center">
                                <Icon name="sync-svgrepo-com" className="w-6 h-6 mx-auto mb-3" style={{ animation: 'spin 1.5s linear infinite' }} />
                                <p className="text-sm text-textSecondary">Loading linkages...</p>
                            </div>
                        </div>
                    ) : filtered.length === 0 ? (
                        <div className="flex items-center justify-center h-full opacity-40">
                            <div className="text-center">
                                <Icon name="taxonomy_table" className="w-10 h-10 mx-auto mb-3 opacity-30" />
                                <p className="text-sm text-textSecondary">No linkages found.</p>
                            </div>
                        </div>
                    ) : (
                        /* LAYER 6 INLINE: The use of <Virtuoso> to enforce the DOM Virtualization Law to prevent
                           browser memory crashes on massive datasets. Only visible rows are rendered in the DOM. */
                        <Virtuoso
                            data={filtered}
                            itemContent={renderRow}
                            className="h-full"
                        />
                    )}
                </div>
            </div>
        </Layout>
    );
};

export default TaxonomyConsole;