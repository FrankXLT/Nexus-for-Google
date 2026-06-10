import { create } from 'zustand';
import axios from 'axios';

const useNexusStore = create((set, get) => ({
    artifacts: [],
    viewMode: 'STAGING_GRID', // 'STAGING_GRID', 'KNOWLEDGE_GRAPH', 'TREEMAP'
    searchQuery: '',
    isLoading: false,
    selectedArtifact: null,
    
    setSearchQuery: (query) => {
        set({ searchQuery: query });
        get().fetchData();
    },
    
    setViewMode: (mode) => {
        set({ viewMode: mode });
        get().fetchData();
    },
    
    setSelectedArtifact: (artifact) => set({ selectedArtifact: artifact }),
    
    fetchData: async () => {
        const { searchQuery } = get();
        set({ isLoading: true });
        try {
            let res;
            if (searchQuery.trim().length > 0) {
                res = await axios.get(`/api/knowledge/search?q=${encodeURIComponent(searchQuery)}&limit=100&offset=0`, { withCredentials: true });
            } else {
                res = await axios.get(`/api/data/artifacts?limit=100&offset=0`, { withCredentials: true });
            }
            set({ artifacts: res.data || [], isLoading: false });
        } catch (error) {
            console.error("Failed to fetch data:", error);
            set({ artifacts: [], isLoading: false });
        }
    }
}));

export default useNexusStore;