import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import useNexusStore from '../store/useNexusStore';
import Icon from './Icon';

/**
 * VQBHeatmap — Activity Heatmap showing top senders over time.
 *
 * Layer Interactions:
 * - Layer 6 (Frontend UI): Renders the heatmap tab of the VQB.
 *
 * State Interactions:
 * - Reads heatmapData from NexusStore.
 *
 * Rendering:
 * - Y-axis: Top senders (up to 25, by volume over last 90 days).
 * - X-axis: Weekly time buckets.
 * - Cell color: Sender's brand hex, intensity normalized to that sender's max.
 * - QUARANTINE override: Cell turns error-red regardless of brand color.
 *
 * @returns {JSX.Element}
 */
const VQBHeatmap = () => {
    const { heatmapData, isVqbLoading } = useNexusStore();

    const option = useMemo(() => {
        if (!heatmapData || heatmapData.senders.length === 0) return null;

        const { senders, buckets, data } = heatmapData;

        // Compute per-sender max for normalization
        const senderMaxMap = {};
        data.forEach(([bucketIdx, senderIdx, val]) => {
            if (senderMaxMap[senderIdx] === undefined || val > senderMaxMap[senderIdx]) {
                senderMaxMap[senderIdx] = val;
            }
        });

        // Find global max for color scaling
        const globalMax = Math.max(...data.map(d => d[2]), 1);

        return {
            backgroundColor: 'transparent',
            tooltip: {
                position: 'top',
                formatter: (params) => {
                    const s = senders[params.data[1]];
                    return `<div style="font-size:12px"><b>${s?.display_name || 'Unknown'}</b><br/>${buckets[params.data[0]] || ''}<br/>${params.data[2]} artifact${params.data[2] !== 1 ? 's' : ''}</div>`;
                }
            },
            grid: {
                top: 10,
                bottom: 40,
                left: 160,
                right: 20,
            },
            xAxis: {
                type: 'category',
                data: buckets,
                splitArea: { show: false },
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: {
                    color: '#6b7280',
                    fontSize: 9,
                    interval: Math.floor(buckets.length / 8),
                }
            },
            yAxis: {
                type: 'category',
                data: senders.map(s => s.display_name),
                splitArea: { show: false },
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: {
                    color: '#9ca3af',
                    fontSize: 10,
                    width: 145,
                    overflow: 'truncate',
                    formatter: (val) => val.length > 22 ? val.slice(0, 22) + '…' : val,
                }
            },
            visualMap: {
                show: false,
                min: 0,
                max: globalMax,
                inRange: { color: ['rgba(106,90,169,0.1)', 'rgba(106,90,169,0.9)'] }
            },
            series: [{
                name: 'Activity',
                type: 'heatmap',
                data: data.map(([bIdx, sIdx, val]) => {
                    const sender = senders[sIdx];
                    const hasQuarantine = sender?.has_quarantine;
                    const senderMax = senderMaxMap[sIdx] || 1;
                    const normalizedIntensity = val / senderMax;

                    // QUARANTINE override: use red regardless of brand color
                    let cellColor;
                    if (hasQuarantine) {
                        cellColor = `rgba(239,68,68,${0.3 + normalizedIntensity * 0.7})`;
                    } else {
                        // Use brand hex with intensity-based opacity
                        const hex = sender?.color_hex || '#6A5AA9';
                        cellColor = hexToRgba(hex, 0.15 + normalizedIntensity * 0.85);
                    }

                    return {
                        value: [bIdx, sIdx, val],
                        itemStyle: { color: cellColor }
                    };
                }),
                emphasis: {
                    itemStyle: {
                        shadowBlur: 10,
                        shadowColor: 'rgba(255,255,255,0.1)'
                    }
                },
                itemStyle: {
                    borderRadius: 2,
                    borderWidth: 0,
                },
                label: { show: false },
            }]
        };
    }, [heatmapData]);

    if (isVqbLoading) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                    <Icon name="sync-svgrepo-com" className="w-6 h-6 opacity-40 mx-auto mb-2" style={{ animation: 'spin 1.5s linear infinite' }} />
                    <p className="text-xs text-muted">Loading activity data...</p>
                </div>
            </div>
        );
    }

    if (!heatmapData || heatmapData.senders.length === 0) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="text-center opacity-40">
                    <Icon name="heatmap_icon" className="w-10 h-10 mx-auto mb-3 opacity-30" />
                    <p className="text-sm font-medium text-textSecondary">No activity data yet</p>
                    <p className="text-xs text-muted mt-1">Artifacts will appear here as Nexus processes your workspace.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-hidden">
            <ReactECharts
                option={option}
                style={{ height: '100%', width: '100%' }}
                opts={{ renderer: 'svg' }}
            />
        </div>
    );
};

// Utility: convert hex to rgba with given opacity
function hexToRgba(hex, alpha) {
    if (!hex || !hex.startsWith('#')) return `rgba(106,90,169,${alpha})`;
    const clean = hex.replace('#', '');
    const full = clean.length === 3 ? clean.split('').map(c => c + c).join('') : clean;
    const r = parseInt(full.slice(0, 2), 16);
    const g = parseInt(full.slice(2, 4), 16);
    const b = parseInt(full.slice(4, 6), 16);
    return `rgba(${r},${g},${b},${alpha})`;
}

export default VQBHeatmap;
