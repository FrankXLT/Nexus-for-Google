import React, { useState, useEffect } from 'react';
import axios from 'axios';
import useNexusStore from '../store/useNexusStore';
import Icon from './Icon';

const ContextModal = () => {
    const { selectedArtifact, setSelectedArtifact } = useNexusStore();
    const [activeTab, setActiveTab] = useState('CONTEXT'); // 'CONTEXT', 'AI_TRACE'
    const [logs, setLogs] = useState([]);
    const [logsLoading, setLogsLoading] = useState(false);

    useEffect(() => {
        if (selectedArtifact && activeTab === 'AI_TRACE') {
            setLogsLoading(true);
            axios.get(`/api/data/audit/${selectedArtifact.id}`, { withCredentials: true })
                .then(res => setLogs(res.data))
                .catch(err => console.error("Failed to fetch AI audit logs", err))
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

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-70 p-4">
            <div className="bg-bgBase border border-gray-700 rounded-xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl">
                <div className="flex items-center justify-between p-4 border-b border-gray-800 bg-bgSurface rounded-t-xl">
                    <h2 className="text-xl font-bold text-textPrimary">Inspector: <span className="font-mono text-sm text-textSecondary">{selectedArtifact.id}</span></h2>
                    <button onClick={handleClose} className="text-gray-400 hover:text-white transition-colors">
                        <Icon name="close-ellipse" className="w-6 h-6" />
                    </button>
                </div>
                
                <div className="flex border-b border-gray-800 bg-bgSurface">
                    <button 
                        className={`flex-1 py-3 text-sm font-semibold transition-colors ${activeTab === 'CONTEXT' ? 'text-accentPrimary border-b-2 border-accentPrimary' : 'text-textSecondary hover:text-white'}`}
                        onClick={() => setActiveTab('CONTEXT')}
                    >
                        Source Context
                    </button>
                    <button 
                        className={`flex-1 py-3 text-sm font-semibold transition-colors ${activeTab === 'AI_TRACE' ? 'text-accentPrimary border-b-2 border-accentPrimary' : 'text-textSecondary hover:text-white'}`}
                        onClick={() => setActiveTab('AI_TRACE')}
                    >
                        AI Trace
                    </button>
                </div>

                <div className="flex-1 overflow-auto p-6">
                    {activeTab === 'CONTEXT' && (
                        <div className="flex flex-col items-center justify-center h-full space-y-4 text-center py-10">
                            <Icon name={selectedArtifact.source_system === 'gmail' ? 'gmail_icon' : 'google_drive_icon'} className="w-16 h-16" />
                            <h3 className="text-lg text-textPrimary">View Original Source</h3>
                            <p className="text-textSecondary max-w-md">Open this artifact securely in Google Workspace to view the native content.</p>
                            <a 
                                href={deepLink} 
                                target="_blank" 
                                rel="noreferrer"
                                className="mt-4 px-6 py-2 bg-accentPrimary text-black font-bold rounded hover:bg-opacity-90 flex items-center gap-2"
                            >
                                Open in Workspace <Icon name="open-external" className="w-4 h-4" />
                            </a>
                        </div>
                    )}
                    
                    {activeTab === 'AI_TRACE' && (
                        <div>
                            {logsLoading ? (
                                <div className="text-textSecondary text-center mt-10">Decrypting telemetry...</div>
                            ) : logs.length === 0 ? (
                                <div className="text-textSecondary text-center mt-10">No AI audit logs found for this artifact.</div>
                            ) : (
                                <div className="space-y-6">
                                    {logs.map((log, i) => (
                                        <div key={log.id || i} className="bg-bgSurface rounded p-4 border border-gray-700">
                                            <div className="flex items-center justify-between mb-4">
                                                <span className="font-bold text-accentPrimary">Pass: {log.prompt_name}</span>
                                                <span className="text-xs font-mono text-gray-500">Tokens: {log.total_tokens} | {log.execution_ms}ms</span>
                                            </div>
                                            
                                            <h4 className="text-xs text-textSecondary uppercase mb-1 font-bold">Request Payload</h4>
                                            <pre className="bg-[#0d0d0d] text-gray-300 p-3 rounded overflow-auto text-xs mb-4 max-h-64 border border-gray-800">
                                                <code>{JSON.stringify(log.request_payload, null, 2)}</code>
                                            </pre>
                                            
                                            <h4 className="text-xs text-textSecondary uppercase mb-1 font-bold">Response Payload</h4>
                                            <pre className="bg-[#0d0d0d] text-green-400 p-3 rounded overflow-auto text-xs max-h-64 border border-gray-800">
                                                <code>{JSON.stringify(log.response_payload, null, 2)}</code>
                                            </pre>
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