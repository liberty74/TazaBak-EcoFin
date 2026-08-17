import React from 'react';
import { Outlet, Navigate } from 'react-router-dom';
import { useAuth } from '../../store/AuthContext';
import { Loader2 } from 'lucide-react';

export const ProtectedRoute = ({ allowedRoles }: { allowedRoles: string[] }) => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/demo" replace />;
  }

  if (!allowedRoles.includes(user.role || '')) {
    // If logged in but wrong role, redirect to appropriate home
    if (user.role === 'dispatcher') return <Navigate to="/dispatcher" replace />;
    return <Navigate to="/home" replace />;
  }

  return <Outlet />;
};
