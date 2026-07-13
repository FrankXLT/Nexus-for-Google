import React, { useEffect, useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import useNexusStore from '../store/useNexusStore';
import Icon from './Icon';

/**
 * Treemap — ECharts Treemap visualization of the taxonomy hierarchy.
 *
 * Layer Interactions:
 * - Layer 6 (Frontend UI): Result view for TREEMAP mode.
 *
 * State Interactions:
 * - Reads taxonomySummary from NexusStore.
 * - Calls fetchTaxonomySummary() on mount if data not cached.
 * - Calls addChip() when a category/entity is clicked (drill-to-search).
 *
 * Rendering:
 * - Level 1: Categories (colored by color_hex).
 * - Level 2: Entities within each category.
 * - Click on any tile → drops chip into Omnibox.
 *
 * @returns {JSX.Element}
 */
const Treemap = () => {
    const { taxonomySummary, fetchTaxonomySummary, addChip } = useNexusStore();

    useEffect(() => {
        if (!taxonomySummary) fetchTaxonomySummary();
    }, []);

    const option = useMemo(() => {
        if (!taxonomySummary || taxonomySummary.children.length === 0) return null;

        const mapNode = (node) => ({
            name: node.name,
            value: node.value,
            itemStyle: { color: node.color_hex },
            children: node.children ? node.children.map(mapNode) : undefined,
        });

        return {
            backgroundColor: 'transparent',
            tooltip: {
                formatter: (info) => {
                    return `<div style="font-size:12px"><b>${info.name}</b><br/>${info.value} artifact${info.value !== 1 ? 's' : ''}</div>`;
                }
            },
            series: [{
                type: 'treemap',
                data: taxonomySummary.children.map(mapNode),
                width: '100%',
                height: '100%',
                roam: false,
                nodeClick: 'zoomToNode',
                breadcrumb: {
                    show: true,
                    bottom: 10,
                    itemStyle: {
                        color: '#1E1E24',
                        borderColor: 'rgba(255,255,255,0.1)',
                        textStyle: { color: '#9ca3af', fontSize: 11 }
                    }
                },
                label: {
                    show: true,
                    formatter: '{b}',
                    color: 'rgba(255,255,255,0.9)',
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 12,
                    fontWeight: 600,
                },
                upperLabel: {
                    show: true,
                    height: 28,
                    formatter: (params) => `  ${params.name} (${params.value})`,
                    color: '#fff',
                    fontWeight: 700,
                    fontSize: 12,
                },
                itemStyle: {
                    borderWidth: 2,
                    borderColor: '#121215',
                    gapWidth: 2,
                },
                emphasis: {
                    label: { fontSize: 14 },
                    itemStyle: { shadowBlur: 20, shadowColor: 'rgba(0,0,0,0.5)' }
                },
                levels: [
                    {
                        // Category level
                        itemStyle: { borderWidth: 3, borderColor: '#0a0a0f', gapWidth: 3 },
                        upperLabel: { show: true }
                    },
                    {
                        // Entity level
                        itemStyle: { borderWidth: 1, borderColor: 'rgba(0,0,0,0.3)', gapWidth: 1 },
                        label: { show: true }
                    }
                ]
            }]
        };
    }, [taxonomySummary]);

    const onChartEvents = useMemo(() => ({
        click: (params) => {
            if (params.data?.name) {
                addChip({
                    type: 'taxonomy',
                    value: params.data.name,
                    label: params.data.name,
                    color: params.data.itemStyle?.color || 'var(--accent-primary)',
                });
            }
        }
    }), [addChip]);

    if (!taxonomySummary) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="text-center">
                    <Icon name="sync-svgrepo-com" className="w-6 h-6 opacity-30 mx-auto mb-3" style={{ animation: 'spin 1.5s linear infinite' }} />
                    <p className="text-sm text-muted">Loading taxonomy...</p>
                </div>
            </div>
        );
    }

    if (taxonomySummary.children.length === 0) {
        return (
            <div className="flex items-center justify-center h-full opacity-40">
                <div className="text-center">
                    <Icon name="treemap_graph_icon" className="w-12 h-12 mx-auto mb-3 opacity-30" />
                    <p className="text-sm font-medium text-textSecondary">No taxonomy data</p>
                    <p className="text-xs text-muted mt-1">Data will appear here as Nexus processes your workspace.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="h-full animate-fade-in">
            <p className="text-xs text-muted mb-2 opacity-60">
                Click a tile to add it as an Omnibox filter · Click category headers to drill down
            </p>
            <ReactECharts
                option={option}
                style={{ height: 'calc(100% - 28px)', width: '100%' }}
                opts={{ renderer: 'svg' }}
                onEvents={onChartEvents}
            />
        </div>
    );
};

export default Treemap;
