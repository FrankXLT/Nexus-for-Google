import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import useNexusStore from '../store/useNexusStore';

const VQBSankey = () => {
    const { artifacts } = useNexusStore();

    const option = useMemo(() => {
        // LAYER 6 INLINE: Maps the flat artifacts array into the exact nodes and links format expected by Apache ECharts. Why ECharts is used instead of Mermaid.js (React 18 Strict Mode lifecycle conflicts).
        // Apache ECharts expects a specific {nodes, links} object. We reduce the flat artifacts array 
        // to aggregate the linkage weights. We utilize ECharts instead of Mermaid.js because Mermaid.js 
        // struggles with React 18's Strict Mode double-render lifecycles, causing overlapping DOM injections.
        const nodesMap = new Map();
        const linksMap = new Map();

        artifacts.forEach(art => {
            const cat = art.category_name || 'Unknown Category';
            const ent = art.entity_name || 'Unknown Entity';
            const purp = art.purpose_name || 'Unknown Purpose';

            nodesMap.set(cat, true);
            nodesMap.set(ent, true);
            nodesMap.set(purp, true);

            const link1 = `${cat}|${ent}`;
            linksMap.set(link1, (linksMap.get(link1) || 0) + 1);

            const link2 = `${ent}|${purp}`;
            linksMap.set(link2, (linksMap.get(link2) || 0) + 1);
        });

        const nodes = Array.from(nodesMap.keys()).map(name => ({ name }));
        const links = Array.from(linksMap.entries()).map(([key, val]) => {
            const [source, target] = key.split('|');
            return { source, target, value: val };
        });

        return {
            tooltip: { trigger: 'item', triggerOn: 'mousemove' },
            series: {
                type: 'sankey',
                layout: 'none',
                emphasis: { focus: 'adjacency' },
                data: nodes,
                links: links,
                lineStyle: { color: 'source', curveness: 0.5 },
                label: { color: 'var(--text-primary)', fontFamily: 'monospace', fontSize: 10 }
            }
        };
    }, [artifacts]);

    if (artifacts.length === 0) return null;

    return (
        <div className="mt-4 border border-gray-800 rounded bg-bgSurface p-4 shadow-inner">
            <h3 className="text-xs text-textSecondary mb-4 font-bold uppercase tracking-wider">Taxonomy Flow (ECharts)</h3>
            <ReactECharts option={option} style={{ height: '250px', width: '100%' }} />
        </div>
    );
};

export default VQBSankey;