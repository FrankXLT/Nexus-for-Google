import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Virtuoso } from 'react-virtuoso';
import Layout from '../components/Layout';

const TaxonomyConsole = () => {
    const [linkages, setLinkages] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchLinkages = () => {
        axios.get('/api/taxonomy/linkages?limit=500&offset=0', { withCredentials: true })
            .then(res => {
                setLinkages(res.data);
                setLoading(false);
            })
            .catch(err => console.error(err));
    };

    useEffect(() => {
        fetchLinkages();
    }, []);

    const handleApprove = (linkageId) => {
        axios.patch(`/api/taxonomy/approve/${linkageId}`, {}, { withCredentials: true })
            .then(() => fetchLinkages())
            .catch(err => console.error(err));
    };

    const renderRow = (index, link) => (
        <div className="flex items-center justify-between p-4 mb-2 bg-bgSurface border border-gray-800 rounded shadow hover:bg-gray-800 transition-colors">
            <div className="flex gap-4 items-center">
                <span className="font-bold text-textPrimary w-32 truncate">{link.category_name || 'N/A'}</span>
                <span className="text-textSecondary w-40 truncate">{link.entity_name || 'N/A'}</span>
                <span className="text-textSecondary w-32 truncate">{link.purpose_name || 'N/A'}</span>
                <span className={`text-xs px-2 py-1 rounded font-mono ${link.nexus_state === 'QUARANTINE' ? 'bg-red-900 text-red-100 border border-red-700' : 'bg-green-900 text-green-100 border border-green-700'}`}>
                    {link.nexus_state}
                </span>
            </div>
            {link.nexus_state === 'QUARANTINE' && (
                <button 
                    onClick={() => handleApprove(link.linkage_id)}
                    className="px-4 py-1.5 bg-accentPrimary text-black text-sm font-bold rounded hover:bg-opacity-80 transition-all shadow-[0_0_10px_rgba(187,134,252,0.3)]"
                >
                    Approve
                </button>
            )}
        </div>
    );

    return (
        <Layout>
            <div className="max-w-6xl mx-auto h-full flex flex-col">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h1 className="text-2xl font-bold text-textPrimary">Taxonomy Matrix</h1>
                        <p className="text-sm text-textSecondary">Manage active mappings and approve quarantined entities.</p>
                    </div>
                    <div className="text-sm font-mono text-gray-500">Total: {linkages.length}</div>
                </div>
                {loading ? (
                    <div className="text-textSecondary flex items-center justify-center h-64">Loading linkages...</div>
                ) : linkages.length === 0 ? (
                    <div className="text-textSecondary flex items-center justify-center h-64">No linkages found in system.</div>
                ) : (
                    <div className="flex-1 overflow-hidden pr-2">
                        <Virtuoso 
                            data={linkages}
                            itemContent={renderRow}
                            className="h-full w-full"
                        />
                    </div>
                )}
            </div>
        </Layout>
    );
};

export default TaxonomyConsole;