import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Icon from './Icon';

const SystemSettingsModal = ({ onClose }) => {
    const [config, setConfig] = useState({});
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);

    useEffect(() => {
        axios.get('/api/system/config', { withCredentials: true })
            .then(res => {
                setConfig(res.data);
                setLoading(false);
            })
            .catch(err => console.error(err));
    }, []);

    const handleSave = () => {
        axios.patch('/api/system/config', config, { withCredentials: true })
            .then(() => onClose())
            .catch(err => console.error(err));
    };

    const handleGenerateTheme = () => {
        setGenerating(true);
        axios.post('/api/system/theme/generate', {}, { withCredentials: true })
            .then(() => window.location.reload())
            .catch(err => {
                console.error(err);
                setGenerating(false);
            });
    };

    if (loading) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-70 p-4">
            <div className="bg-bgBase border border-gray-700 rounded-xl w-full max-w-lg shadow-2xl flex flex-col max-h-[90vh]">
                <div className="flex items-center justify-between p-4 border-b border-gray-800 bg-bgSurface rounded-t-xl">
                    <h2 className="text-xl font-bold text-textPrimary">System Settings</h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                        <Icon name="close-ellipse" className="w-6 h-6" />
                    </button>
                </div>
                <div className="p-6 space-y-4 overflow-y-auto">
                    <div>
                        <label className="block text-xs text-textSecondary uppercase mb-1 font-bold">Drive Log Retention (Days)</label>
                        <input 
                            type="number" 
                            value={config.drive_log_retention_days || ''} 
                            onChange={e => setConfig({...config, drive_log_retention_days: e.target.value})}
                            className="w-full bg-bgSurface text-textPrimary border border-gray-700 rounded p-2 focus:border-accentPrimary outline-none transition-colors"
                        />
                    </div>
                    <div>
                        <label className="block text-xs text-textSecondary uppercase mb-1 font-bold">DB Audit Retention (Days)</label>
                        <input 
                            type="number" 
                            value={config.db_audit_retention_days || ''} 
                            onChange={e => setConfig({...config, db_audit_retention_days: e.target.value})}
                            className="w-full bg-bgSurface text-textPrimary border border-gray-700 rounded p-2 focus:border-accentPrimary outline-none transition-colors"
                        />
                    </div>
                    <div>
                        <label className="block text-xs text-textSecondary uppercase mb-1 font-bold">Ignored Gmail Categories (CSV)</label>
                        <textarea 
                            value={config.ignored_gmail_categories || ''} 
                            onChange={e => setConfig({...config, ignored_gmail_categories: e.target.value})}
                            className="w-full bg-bgSurface text-textPrimary border border-gray-700 rounded p-2 h-20 focus:border-accentPrimary outline-none transition-colors resize-none"
                            placeholder="promotions, social, forums..."
                        ></textarea>
                    </div>
                    <div>
                        <label className="block text-xs text-textSecondary uppercase mb-1 font-bold">Domain Blocklist (CSV)</label>
                        <textarea 
                            value={config.domain_blocklist || ''} 
                            onChange={e => setConfig({...config, domain_blocklist: e.target.value})}
                            className="w-full bg-bgSurface text-textPrimary border border-gray-700 rounded p-2 h-20 focus:border-accentPrimary outline-none transition-colors resize-none"
                            placeholder="marketing@spam.com, noreply@*"
                        ></textarea>
                    </div>
                    <div className="border-t border-gray-800 pt-4 mt-4">
                        <h3 className="text-sm font-bold text-textPrimary mb-2 flex items-center gap-2">
                            <Icon name="setting-config" className="w-4 h-4 text-accentPrimary" />
                            Chromatic Engine Generator
                        </h3>
                        <p className="text-xs text-textSecondary mb-3">Uses Gemini 2.5 Pro to procedurally generate global CSS variables and update database entity hex codes based on semantic clusters.</p>
                        <button 
                            onClick={handleGenerateTheme}
                            disabled={generating}
                            className="w-full px-4 py-3 bg-accentPrimary text-black font-bold rounded hover:bg-opacity-90 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
                        >
                            {generating ? (
                                <>Generating... <span className="animate-spin">🌀</span></>
                            ) : "Generate & Apply Theme"}
                        </button>
                    </div>
                </div>
                <div className="p-4 border-t border-gray-800 flex justify-end gap-2 bg-bgSurface rounded-b-xl shrink-0">
                    <button onClick={onClose} className="px-6 py-2 text-textPrimary hover:bg-gray-800 rounded font-semibold transition-colors">Cancel</button>
                    <button onClick={handleSave} className="px-6 py-2 bg-green-700 text-white font-bold rounded hover:bg-green-600 transition-colors shadow-lg">Save Configuration</button>
                </div>
            </div>
        </div>
    );
};

export default SystemSettingsModal;