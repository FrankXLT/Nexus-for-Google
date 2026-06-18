import { create } from 'zustand';
import axios from 'axios';

const useNexusStore = create((set, get) => ({
    artifacts: [],
    viewMode: 'STAGING_GRID',
    searchQuery: '',
    searchScope: 'NEXUS', // 'NEXUS', 'GMAIL'
    isLoading: false,
    selectedArtifact: null,
    
    setSearchQuery: (query) => {
        set({ searchQuery: query });
        get().fetchData();
    },
    
    setSearchScope: (scope) => {
        set({ searchScope: scope, artifacts: [], selectedArtifact: null });
        get().fetchData();
    },
    
    setViewMode: (mode) => {
        set({ viewMode: mode });
        get().fetchData();
    },
    
    setSelectedArtifact: (artifact) => set({ selectedArtifact: artifact }),
    
    fetchData: async () => {
        const { searchQuery, searchScope } = get();
        set({ isLoading: true });
        try {
            let res;
            if (searchScope === 'GMAIL') {
                if (searchQuery.trim().length > 0) {
                    res = await axios.get(`/api/proxy/search?q=${encodeURIComponent(searchQuery)}&source=gmail`, { withCredentials: true });
                    set({ artifacts: res.data || [], isLoading: false });
                } else {
                    set({ artifacts: [], isLoading: false });
                }
            } else {
                if (searchQuery.trim().length > 0) {
                    res = await axios.get(`/api/knowledge/search?q=${encodeURIComponent(searchQuery)}&limit=100&offset=0`, { withCredentials: true });
                } else {
                    res = await axios.get(`/api/data/artifacts?limit=100&offset=0`, { withCredentials: true });
                }
                set({ artifacts: res.data || [], isLoading: false });
            }
        } catch (error) {
            console.error("Failed to fetch data:", error);
            set({ artifacts: [], isLoading: false });
        }
    }
}));

export default useNexusStore;
