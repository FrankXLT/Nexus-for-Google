import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';
import axios from 'axios';
import { useAuth } from './AuthProvider';
import Icon from '../components/Icon';

/**
 * Login page with Google SSO authentication.
 *
 * Layer Interactions:
 * - Layer 6 (Frontend UI): Full-page login view.
 * - Layer 1 (Foundation): Passes Google ID token to FastAPI for verification.
 *
 * State Interactions:
 * - Reads/writes AuthContext isAuthenticated state.
 *
 * @returns {JSX.Element}
 */
const Login = () => {
    const { login, isAuthenticated } = useAuth();
    const navigate = useNavigate();

    useEffect(() => {
        if (isAuthenticated) navigate('/', { replace: true });
    }, [isAuthenticated, navigate]);

    const onSuccess = async (credentialResponse) => {
        try {
            await axios.post('/api/auth/google', { id_token: credentialResponse.credential }, { withCredentials: true });
            login(credentialResponse.credential);
            navigate('/', { replace: true });
        } catch (error) {
            console.error('Login failed', error);
            alert('Login Failed: ' + (error.response?.data?.detail || error.message));
        }
    };

    return (
        <div className="flex flex-col items-center justify-center min-h-screen login-bg relative overflow-hidden">
            {/* Background grid lines */}
            <div className="absolute inset-0 opacity-5" style={{
                backgroundImage: 'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
                backgroundSize: '60px 60px'
            }} />

            {/* Glow orb */}
            <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full opacity-10 blur-3xl pointer-events-none"
                style={{ background: 'var(--accent-primary, #6A5AA9)' }} />

            {/* Login Card */}
            <div className="relative z-10 w-full max-w-sm animate-fade-in">
                <div className="nexus-card p-8 flex flex-col items-center">
                    {/* Logo */}
                    <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5"
                        style={{
                            background: 'linear-gradient(135deg, var(--accent-primary, #6A5AA9) 0%, #4a3a89 100%)',
                            boxShadow: '0 8px 32px rgba(106, 90, 169, 0.4)'
                        }}>
                        <Icon name="google-gemini-logo" className="w-9 h-9" />
                    </div>

                    <h1 className="text-2xl font-bold text-textPrimary mb-1">Nexus</h1>
                    <p className="text-sm text-textSecondary mb-6 text-center">Your Workspace Intelligence Layer</p>

                    <div className="w-full border-t mb-6" style={{ borderColor: 'rgba(255,255,255,0.06)' }} />

                    <p className="text-xs text-muted mb-4 uppercase tracking-widest font-semibold">Sign in with Google</p>

                    <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID}>
                        <GoogleLogin
                            onSuccess={onSuccess}
                            onError={() => alert('Google Popup Login Failed.')}
                            theme="filled_black"
                            size="large"
                            width="280"
                        />
                    </GoogleOAuthProvider>

                    <p className="text-xs text-muted mt-6 text-center opacity-60">
                        Access restricted to authorized accounts only.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default Login;