import React, { createContext, useContext, useEffect, useState } from 'react';
import axios from 'axios';

const ThemeContext = createContext();

export const useTheme = () => useContext(ThemeContext);

export const ThemeProvider = ({ children }) => {
    const [theme, setTheme] = useState({
        "--bg-base": "#121212",
        "--bg-surface": "#1e1e1e",
        "--text-primary": "#ffffff",
        "--text-secondary": "#b3b3b3",
        "--accent-primary": "#bb86fc"
    });

    useEffect(() => {
        axios.get('/api/data/theme', { withCredentials: true })
            .then(res => {
                if (res.data) {
                    setTheme(res.data);
                }
            })
            .catch(err => {
                console.error("Failed to load theme, using fallback", err);
            });
    }, []);

    useEffect(() => {
        // LAYER 7 INLINE: The Chromatic Engine Law—how the fetched theme JSON is iterated over and injected into document.documentElement.style to dynamically override CSS variables.
        // We iterate through the JSON dictionary provided by the backend to dynamically apply colors to the DOM.
        // This injects the variables directly into the :root CSS selector, instantly updating the UI theme.
        const root = document.documentElement;
        Object.entries(theme).forEach(([key, value]) => {
            root.style.setProperty(key, value);
        });
    }, [theme]);

    return (
        <ThemeContext.Provider value={{ theme }}>
            {children}
        </ThemeContext.Provider>
    );
};