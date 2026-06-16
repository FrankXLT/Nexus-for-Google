import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';
import axios from 'axios';
import { useAuth } from './AuthProvider';
import Icon from '../components/Icon';

const Login = () => {
    const { login, isAuthenticated } = useAuth();
    const navigate = useNavigate();

    useEffect(() => {
        if (isAuthenticated) {
            navigate('/', { replace: true });
        }
    }, [isAuthenticated, navigate]);

    const onSuccess = async (credentialResponse) => {
        try {
            await axios.post('/api/auth/google', { id_token: credentialResponse.credential }, { withCredentials: true });
            login(credentialResponse.credential);
            navigate('/', { replace: true });
        } catch (error) {
            console.error("Login failed", error);
            alert("Login Failed: " + (error.response?.data?.detail || error.message));
        }
    };

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-bgBase">
            <div className="p-8 bg-bgSurface rounded-xl shadow-lg flex flex-col items-center">
                <Icon name="google-gemini-logo" className="w-16 h-16 mb-4" />
                <h1 className="text-2xl font-bold text-textPrimary mb-6">Nexus Login</h1>
                <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID}>
                    <GoogleLogin
                        onSuccess={onSuccess}
                        onError={() => {
                            console.log('Login Failed');
                            alert('Google Popup Login Failed.');
                        }}
                    />
                </GoogleOAuthProvider>
            </div>
        </div>
    );
};

export default Login;
