import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeProvider';
import { AuthProvider, useAuth } from './auth/AuthProvider';
import Login from './auth/Login';
import Dashboard from './pages/Dashboard';
import TaxonomyConsole from './pages/TaxonomyConsole';

const ProtectedRoute = ({ children }) => {
    const { isAuthenticated } = useAuth();
    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }
    return children;
};

/**
 * Main application routing and protection layer.
 *
 * Layer Interactions:
 * - Layer 6 (Frontend UI)
 *
 * State Interactions:
 * - None
 *
 * @returns {JSX.Element}
 */
const App = () => {
    return (
        <ThemeProvider>
            <AuthProvider>
                <Router>
                    <Routes>
                        <Route path="/login" element={<Login />} />
                        <Route path="/" element={
                            <ProtectedRoute>
                                <Dashboard />
                            </ProtectedRoute>
                        } />
                        <Route path="/console" element={
                            <ProtectedRoute>
                                <TaxonomyConsole />
                            </ProtectedRoute>
                        } />
                    </Routes>
                </Router>
            </AuthProvider>
        </ThemeProvider>
    );
};

export default App;