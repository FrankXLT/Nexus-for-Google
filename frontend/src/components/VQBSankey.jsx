import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import useNexusStore from '../store/useNexusStore';
import Icon from './Icon';

/**
 * VQBSankey — Taxonomy Flow Sankey diagram.
 *
 * Layer Interactions:
 * - Layer 6 (Frontend UI): Renders the Sankey tab of the VQB.
 *
 * State Interactions:
 * - Reads sankeyData from NexusStore.
 * - Calls addChip() when a node is clicked.
 *
 * Behavior:
 * - Fetches nodes/links from /api/taxonomy/vqb (pre-built, colored from taxonomy DB).
 * - Clicking a node drops a chip into the Omnibox (no search fired).
 *
 * @returns {JSX.Element}
 */
const VQBSankey = () => {
    const { sankeyData, isVqbLoading, addChip } = useNexusStore();

    const option = useMemo(() => {
        if (!sankeyData || sankeyData.nodes.length === 0) return null;

        return {
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'item',
                triggerOn: 'mousemove',
                formatter: (params) => {
                    if (params.dataType === 'node') {
                        return `<b>${params.data.name}</b>`;
                    }
                    return `${params.data.source} → ${params.data.target}: <b>${params.data.value}</b>`;
                }
            },
            series: [{
                type: 'sankey',
                layout: 'none',
                nodeAlign: 'left',
                emphasis: { focus: 'adjacency' },
                data: sankeyData.nodes,
                links: sankeyData.links,
                lineStyle: {
                    color: 'source',
                    curveness: 0.5,
                    opacity: 0.25,
                },
                label: {
                    color: '#9ca3af',
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 11,
                },
                itemStyle: {
                    borderWidth: 0,
                    borderRadius: 4,
                }
            }]
        };
    }, [sankeyData]);

    const onChartEvents = useMemo(() => ({
        click: (params) => {
            if (params.dataType === 'node') {
                const color = params.data?.itemStyle?.color || 'var(--accent-primary)';
                addChip({
                    type: 'taxonomy',
                    value: params.data.name,
                    label: params.data.name,
                    color: typeof color === 'string' ? color : 'var(--accent-primary)',
                });
            }
        }
    }), [addChip]);

    if (isVqbLoading) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                    <Icon name="sync-svgrepo-com" className="w-6 h-6 opacity-40 mx-auto mb-2" style={{ animation: 'spin 1.5s linear infinite' }} />
                    <p className="text-xs text-muted">Loading taxonomy flow...</p>
                </div>
            </div>
        );
    }

    if (!sankeyData || sankeyData.nodes.length === 0) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="text-center opacity-40">
                    <Icon name="taxonomy_flow_icon" className="w-10 h-10 mx-auto mb-3 opacity-30" />
                    <p className="text-sm font-medium text-textSecondary">No taxonomy data yet</p>
                    <p className="text-xs text-muted mt-1">Taxonomy linkages will appear here after artifacts are processed.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-hidden">
            <p className="text-xs text-muted px-2 mb-2 opacity-60">
                Click a node to add it as an Omnibox filter chip
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

export default VQBSankey;