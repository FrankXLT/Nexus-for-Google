import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Virtuoso } from 'react-virtuoso';
import Layout from '../components/Layout';
import Icon from '../components/Icon';

/**
 * TaxonomyConsole — Two-panel taxonomy management console.
 *
 * Layer Interactions:
 * - Layer 6 (Frontend UI)
 * - Layer 2 (Data Ontology): Reads Categories, Entities, Purposes, Taxonomy Linkages.
 *
 * Panel A — Taxonomy Tree:
 *   Browse the 17 default Categories, their Entities, and the 21 Purposes.
 *   Click a Category to expand its entities. Approved linkages shown inline.
 *
 * Panel B — Linkage Queue:
 *   Manage TAXONOMY_LINKAGES. Approve quarantined entries.
 *   Filter: ALL | QUARANTINE | ACTIVE.
 *
 * State Interactions:
 * - Reads CATEGORIES, ENTITIES, PURPOSES via new /api/taxonomy/tree endpoint.
 * - Reads TAXONOMY_LINKAGES via /api/taxonomy/linkages.
 * - Calls /api/taxonomy/approve/{id} for quarantine approval.
 *
 * @returns {JSX.Element}
 */
const TaxonomyConsole = () => {
    const [activePanel, setActivePanel] = useState('TREE'); // 'TREE' | 'QUEUE'

    // ── Tree State ──
    const [treeData, setTreeData] = useState(null);
    const [treeLoading, setTreeLoading] = useState(true);
    const [expandedCat, setExpandedCat] = useState(null);

    // ── Queue State ──
    const [linkages, setLinkages] = useState([]);
    const [linkageFilter, setLinkageFilter] = useState('ALL');
    const [linkagesLoading, setLinkagesLoading] = useState(false);

    // ── Fetch taxonomy tree ──
    const fetchTree = useCallback(() => {
        setTreeLoading(true);
        axios.get('/api/taxonomy/tree', { withCredentials: true })
            .then(res => { setTreeData(res.data); setTreeLoading(false); })
            .catch(() => setTreeLoading(false));
    }, []);

    // ── Fetch linkage queue ──
    const fetchLinkages = useCallback(() => {
        setLinkagesLoading(true);
        axios.get('/api/taxonomy/linkages?limit=500&offset=0', { withCredentials: true })
            .then(res => { setLinkages(res.data); setLinkagesLoading(false); })
            .catch(() => setLinkagesLoading(false));
    }, []);

    useEffect(() => { fetchTree(); }, [fetchTree]);
    useEffect(() => {
        if (activePanel === 'QUEUE') fetchLinkages();
    }, [activePanel, fetchLinkages]);

    const handleApprove = (linkageId) => {
        axios.patch(`/api/taxonomy/approve/${linkageId}`, {}, { withCredentials: true })
            .then(() => fetchLinkages())
            .catch(err => console.error(err));
    };

    const quarantineCount = linkages.filter(l => l.nexus_state === 'QUARANTINE').length;
    const filteredLinkages = linkageFilter === 'ALL'
        ? linkages
        : linkages.filter(l => l.nexus_state === linkageFilter);

    return (
        <Layout>
            <div className="h-full flex flex-col" style={{ gap: '16px' }}>

                {/* ── Header Card ── */}
                <div className="nexus-card p-5 pt-10 relative shrink-0">
                    <div className="offset-header offset-header-accent">
                        <Icon name="taxonomy_flow_icon" className="w-5 h-5" style={{ filter: 'brightness(10)' }} />
                    </div>

                    <div className="flex items-center justify-between">
                        <div className="ml-12">
                            <h1 className="text-xl font-bold text-textPrimary">Taxonomy Matrix</h1>
                            <p className="text-sm text-textSecondary mt-0.5">
                                Browse the knowledge taxonomy and manage entity associations.
                            </p>
                        </div>

                        <div className="flex items-center gap-3">
                            {quarantineCount > 0 && (
                                <span className="state-badge state-badge-quarantine">
                                    {quarantineCount} Quarantined
                                </span>
                            )}
                            {/* Panel Toggle */}
                            <div className="flex items-center gap-1 rounded-lg p-1" style={{ background: 'var(--bg-base)' }}>
                                <button
                                    onClick={() => setActivePanel('TREE')}
                                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md transition-all"
                                    style={{
                                        background: activePanel === 'TREE' ? 'var(--bg-surface)' : 'transparent',
                                        color: activePanel === 'TREE' ? '#fff' : '#6b7280',
                                    }}
                                >
                                    <Icon name="taxonomy_table" className="w-3.5 h-3.5" />
                                    Taxonomy Tree
                                </button>
                                <button
                                    onClick={() => { setActivePanel('QUEUE'); fetchLinkages(); }}
                                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md transition-all"
                                    style={{
                                        background: activePanel === 'QUEUE' ? 'var(--bg-surface)' : 'transparent',
                                        color: activePanel === 'QUEUE' ? '#fff' : '#6b7280',
                                    }}
                                >
                                    <Icon name="flow-branch" className="w-3.5 h-3.5" />
                                    Linkage Queue
                                    {quarantineCount > 0 && (
                                        <span className="ml-1 px-1.5 py-0.5 rounded-full text-xs font-bold text-white"
                                            style={{ background: '#ef4444', fontSize: '10px' }}>
                                            {quarantineCount}
                                        </span>
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                {/* ══════════════════════════════════════════════
                    PANEL A — TAXONOMY TREE
                    Shows all 17 Categories with entity counts,
                    expandable to list entities and their entity color.
                    ══════════════════════════════════════════════ */}
                {activePanel === 'TREE' && (
                    <div className="flex-1 overflow-hidden" style={{ minHeight: 0 }}>
                        {treeLoading ? (
                            <div className="flex items-center justify-center h-full opacity-40">
                                <div className="text-center">
                                    <Icon name="sync-svgrepo-com" className="w-6 h-6 mx-auto mb-2" style={{ animation: 'spin 1.5s linear infinite' }} />
                                    <p className="text-sm text-textSecondary">Loading taxonomy tree...</p>
                                </div>
                            </div>
                        ) : !treeData ? (
                            <div className="flex items-center justify-center h-full opacity-40">
                                <p className="text-sm text-textSecondary">No taxonomy data found. Ensure db_init.py has run.</p>
                            </div>
                        ) : (
                            <div className="h-full overflow-auto pr-1" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', alignContent: 'start' }}>
                                {treeData.categories.map(cat => (
                                    <CategoryCard
                                        key={cat.id}
                                        cat={cat}
                                        isExpanded={expandedCat === cat.id}
                                        onToggle={() => setExpandedCat(prev => prev === cat.id ? null : cat.id)}
                                    />
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* ══════════════════════════════════════════════
                    PANEL B — LINKAGE QUEUE
                    Shows TAXONOMY_LINKAGES with approve button.
                    ══════════════════════════════════════════════ */}
                {activePanel === 'QUEUE' && (
                    <div className="flex-1 flex flex-col overflow-hidden" style={{ minHeight: 0, gap: '8px' }}>
                        {/* Filter + Refresh bar */}
                        <div className="flex items-center gap-3 shrink-0">
                            <div className="flex items-center gap-1 rounded-lg p-1" style={{ background: 'var(--bg-surface)' }}>
                                {['ALL', 'QUARANTINE', 'ACTIVE'].map(f => (
                                    <button
                                        key={f}
                                        onClick={() => setLinkageFilter(f)}
                                        className="px-3 py-1.5 text-xs font-semibold rounded-md transition-all"
                                        style={{
                                            background: linkageFilter === f ? 'rgba(106,90,169,0.2)' : 'transparent',
                                            color: linkageFilter === f ? '#fff' : '#6b7280',
                                            border: linkageFilter === f ? '1px solid rgba(106,90,169,0.4)' : '1px solid transparent',
                                        }}
                                    >
                                        {f}
                                    </button>
                                ))}
                            </div>
                            <span className="text-xs text-muted font-mono">
                                {filteredLinkages.length} linkage{filteredLinkages.length !== 1 ? 's' : ''}
                            </span>
                            <button onClick={fetchLinkages} className="ml-auto p-2 rounded-lg hover:bg-white hover:bg-opacity-5 transition-colors">
                                <Icon name="sync-svgrepo-com" className="w-4 h-4 opacity-50" />
                            </button>
                        </div>

                        {/* Column headers */}
                        <div className="flex items-center px-4 gap-5 shrink-0">
                            <span className="text-xs text-muted uppercase font-bold tracking-wider w-36">Category</span>
                            <span className="text-xs text-muted uppercase font-bold tracking-wider w-52">Entity</span>
                            <span className="text-xs text-muted uppercase font-bold tracking-wider w-32">Purpose</span>
                            <span className="text-xs text-muted uppercase font-bold tracking-wider">State</span>
                            <span className="text-xs text-muted uppercase font-bold tracking-wider ml-auto pr-4">Last Active</span>
                        </div>

                        {/* Rows */}
                        <div className="flex-1 overflow-hidden">
                            {linkagesLoading ? (
                                <div className="flex items-center justify-center h-full opacity-40">
                                    <Icon name="sync-svgrepo-com" className="w-6 h-6 mx-auto" style={{ animation: 'spin 1.5s linear infinite' }} />
                                </div>
                            ) : filteredLinkages.length === 0 ? (
                                <div className="flex items-center justify-center h-full opacity-40">
                                    <p className="text-sm text-textSecondary">No {linkageFilter !== 'ALL' ? linkageFilter.toLowerCase() + ' ' : ''}linkages found.</p>
                                </div>
                            ) : (
                                /* LAYER 6 INLINE: DOM Virtualization Law — Virtuoso renders only visible rows. */
                                <Virtuoso
                                    data={filteredLinkages}
                                    itemContent={(_, link) => <LinkageRow link={link} onApprove={handleApprove} />}
                                    className="h-full"
                                />
                            )}
                        </div>
                    </div>
                )}
            </div>
        </Layout>
    );
};

/* ── Category Card (Tree Panel) ── */
const CategoryCard = ({ cat, isExpanded, onToggle }) => (
    <div
        className="nexus-card overflow-hidden"
        style={{ '--card-accent': cat.color_hex }}
    >
        {/* Category Header — clickable */}
        <div
            className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-white hover:bg-opacity-3 transition-colors"
            onClick={onToggle}
        >
            <div className="w-3 h-3 rounded-full shrink-0" style={{ background: cat.color_hex }} />
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-textPrimary">{cat.name}</span>
                    <span className="text-xs text-muted font-mono">
                        {cat.entity_count} {cat.entity_count === 1 ? 'entity' : 'entities'}
                    </span>
                </div>
                <p className="text-xs text-muted mt-0.5 leading-snug line-clamp-1 opacity-70">{cat.description}</p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
                <span
                    className="text-xs px-2 py-0.5 rounded font-mono"
                    style={{ background: 'rgba(255,255,255,0.05)', color: '#6b7280' }}
                >
                    {cat.gmail_sync_mode}
                </span>
                <Icon
                    name="chevron-right"
                    className="w-3.5 h-3.5 opacity-30 transition-transform"
                    style={{ transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)' }}
                />
            </div>
        </div>

        {/* Entity list — shown when expanded */}
        {isExpanded && (
            <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                {cat.entities.length === 0 ? (
                    <div className="px-4 py-3 text-xs text-muted opacity-50 italic">
                        No entities yet — will be auto-discovered from your Workspace.
                    </div>
                ) : (
                    cat.entities.map(ent => (
                        <div
                            key={ent.id}
                            className="flex items-center gap-3 px-4 py-2.5 hover:bg-white hover:bg-opacity-3 transition-colors"
                            style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}
                        >
                            <div className="w-2 h-2 rounded-full shrink-0 opacity-80"
                                style={{ background: ent.primary_color_hex || cat.color_hex }}
                            />
                            <span className="text-sm text-textSecondary flex-1 truncate">{ent.canonical_name}</span>
                            {ent.workspace_alias && (
                                <span className="text-xs font-mono text-muted opacity-60">{ent.workspace_alias}</span>
                            )}
                            {ent.active_linkage_count > 0 && (
                                <span
                                    className="text-xs px-2 py-0.5 rounded-full font-semibold"
                                    style={{ background: 'rgba(52,211,153,0.1)', color: '#34d399', border: '1px solid rgba(52,211,153,0.2)' }}
                                >
                                    {ent.active_linkage_count} ACTIVE
                                </span>
                            )}
                            {ent.quarantine_linkage_count > 0 && (
                                <span className="state-badge state-badge-quarantine">
                                    {ent.quarantine_linkage_count} QUARANTINE
                                </span>
                            )}
                        </div>
                    ))
                )}
            </div>
        )}
    </div>
);

/* ── Linkage Row (Queue Panel) ── */
const LinkageRow = ({ link, onApprove }) => {
    const isQuarantine = link.nexus_state === 'QUARANTINE';
    return (
        <div
            className={`flex items-center justify-between px-4 py-3 mb-2 rounded-xl transition-all ${isQuarantine ? 'row-quarantine' : ''}`}
            style={{
                background: isQuarantine ? 'rgba(239,68,68,0.04)' : 'var(--bg-surface)',
                border: isQuarantine ? '1px solid rgba(239,68,68,0.25)' : '1px solid rgba(255,255,255,0.05)',
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
                <div className="flex items-center gap-2 w-52 shrink-0">
                    {link.entity_color_hex && (
                        <div className="w-2 h-2 rounded-full shrink-0 opacity-70" style={{ background: link.entity_color_hex }} />
                    )}
                    <span className="text-sm text-textSecondary truncate">{link.entity_name || '—'}</span>
                </div>
                {/* Purpose */}
                <div className="w-32 shrink-0">
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
                {/* State */}
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
                        onClick={() => onApprove(link.linkage_id)}
                        className="px-4 py-1.5 text-sm font-bold rounded-lg transition-all"
                        style={{ background: 'var(--accent-primary)', color: '#000', boxShadow: '0 0 14px rgba(106,90,169,0.3)' }}
                    >
                        Approve
                    </button>
                )}
            </div>
        </div>
    );
};

export default TaxonomyConsole;