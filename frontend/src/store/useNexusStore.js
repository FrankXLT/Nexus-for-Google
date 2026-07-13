import { create } from 'zustand';
import axios from 'axios';

/**
 * Central Zustand store for all volatile dashboard state.
 *
 * Layer Interactions:
 * - Layer 6 (Frontend UI): Feeds all Dashboard components.
 *
 * State Slices:
 * - artifacts:      Current result set for the active view.
 * - viewMode:       'STAGING_GRID' | 'KNOWLEDGE_GRAPH' | 'TREEMAP'
 * - searchScope:    'NEXUS' | 'GMAIL'
 * - searchQuery:    Current raw text input (not yet committed to search).
 * - chips:          Array of { type, value, label, color } objects in the Omnibox.
 * - isExploreMode:  true = VQB fullscreen; false = results fullscreen.
 * - vqbTab:         'HEATMAP' | 'SANKEY'
 * - heatmapData:    Response from /api/data/heatmap
 * - sankeyData:     Response from /api/taxonomy/vqb
 * - taxonomySummary: Response from /api/data/taxonomy/summary
 * - isLoading:      Spinner flag for result area.
 * - isVqbLoading:   Spinner flag for VQB panel.
 * - selectedArtifact: Currently open ContextModal artifact.
 */
const useNexusStore = create((set, get) => ({
    // ── Results State ──
    artifacts: [],
    viewMode: 'STAGING_GRID',
    searchQuery: '',
    searchScope: 'NEXUS',
    isLoading: false,
    selectedArtifact: null,

    // ── Omnibox Chips ──
    chips: [],

    // ── Explore vs Search Mode ──
    // isExploreMode = true: VQB fills the screen, no search fired yet.
    // isExploreMode = false: VQB slides out, results panel takes over.
    isExploreMode: true,

    // ── VQB State ──
    vqbTab: 'HEATMAP',   // 'HEATMAP' | 'SANKEY'
    heatmapData: null,
    sankeyData: null,
    isVqbLoading: false,

    // ── Taxonomy for Treemap ──
    taxonomySummary: null,

    // ── Actions ──

    setSearchQuery: (query) => set({ searchQuery: query }),

    setSearchScope: (scope) => set({ searchScope: scope, artifacts: [], selectedArtifact: null }),

    setViewMode: (mode) => {
        set({ viewMode: mode });
        // If switching to treemap and no data, fetch it
        if (mode === 'TREEMAP' && !get().taxonomySummary) {
            get().fetchTaxonomySummary();
        }
    },

    setSelectedArtifact: (artifact) => set({ selectedArtifact: artifact }),

    setVqbTab: (tab) => set({ vqbTab: tab }),

    // ── Chip Management (Omnibox) ──
    addChip: (chip) => {
        const { chips } = get();
        // Prevent duplicate chips of the same value
        if (chips.find(c => c.value === chip.value && c.type === chip.type)) return;
        set({ chips: [...chips, chip] });
    },

    removeChip: (index) => {
        const { chips } = get();
        const newChips = chips.filter((_, i) => i !== index);
        set({ chips: newChips });
    },

    clearChips: () => set({ chips: [] }),

    // ── Search Execution ──
    // Called explicitly when the user presses the Search button.
    // Transitions from Explore Mode to Search Mode.
    executeSearch: () => {
        const { searchQuery, chips, viewMode } = get();

        // Build the full query string from text + chips
        const chipText = chips.map(c => c.value).join(' ');
        const fullQuery = [chipText, searchQuery].filter(Boolean).join(' ').trim();

        set({ isExploreMode: false });
        get().fetchData(fullQuery);

        // If no results view is selected yet, default to appropriate one
        if (viewMode === 'STAGING_GRID') {
            set({ viewMode: 'KNOWLEDGE_GRAPH' });
        }
    },

    // ── Return to Explore Mode ──
    returnToExplore: () => {
        set({ isExploreMode: true, artifacts: [] });
        // Refresh VQB data
        get().fetchHeatmap();
        get().fetchSankeyVqb();
    },

    // ── Data Fetching ──
    fetchData: async (queryOverride) => {
        const { searchQuery, searchScope, viewMode, chips } = get();
        const chipText = chips.map(c => c.value).join(' ');
        const query = queryOverride ?? [chipText, searchQuery].filter(Boolean).join(' ').trim();

        set({ isLoading: true });
        try {
            let res;
            if (searchScope === 'GMAIL') {
                if (query.length > 0) {
                    res = await axios.get(`/api/proxy/search?q=${encodeURIComponent(query)}&source=gmail`, { withCredentials: true });
                    set({ artifacts: res.data || [], isLoading: false });
                } else {
                    set({ artifacts: [], isLoading: false });
                }
            } else {
                if (query.length > 0) {
                    res = await axios.get(`/api/knowledge/search?q=${encodeURIComponent(query)}&limit=100&offset=0`, { withCredentials: true });
                } else {
                    res = await axios.get('/api/data/artifacts?limit=100&offset=0', { withCredentials: true });
                }
                set({ artifacts: res.data || [], isLoading: false });
            }
        } catch (error) {
            console.error('Failed to fetch data:', error);
            set({ artifacts: [], isLoading: false });
        }
    },

    fetchHeatmap: async (days = 90) => {
        set({ isVqbLoading: true });
        try {
            const res = await axios.get(`/api/data/heatmap?days=${days}`, { withCredentials: true });
            set({ heatmapData: res.data, isVqbLoading: false });
        } catch (error) {
            console.error('Failed to fetch heatmap:', error);
            set({ isVqbLoading: false });
        }
    },

    fetchSankeyVqb: async () => {
        set({ isVqbLoading: true });
        try {
            const res = await axios.get('/api/taxonomy/vqb', { withCredentials: true });
            set({ sankeyData: res.data, isVqbLoading: false });
        } catch (error) {
            console.error('Failed to fetch sankey VQB data:', error);
            set({ isVqbLoading: false });
        }
    },

    fetchTaxonomySummary: async () => {
        try {
            const res = await axios.get('/api/data/taxonomy/summary', { withCredentials: true });
            set({ taxonomySummary: res.data });
        } catch (error) {
            console.error('Failed to fetch taxonomy summary:', error);
        }
    },
}));

export default useNexusStore;
