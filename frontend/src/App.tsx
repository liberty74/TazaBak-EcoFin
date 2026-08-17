import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './store/AuthContext';
import { LocaleThemeProvider } from './store/LocaleThemeContext';
import { ProtectedRoute } from './components/layout/ProtectedRoute';
import { Toaster } from 'sonner';
import AppLayout from './components/layout/AppLayout';
import DispatcherLayout from './components/layout/DispatcherLayout';
import DispatcherKeyGate from './components/layout/DispatcherKeyGate';
const DemoPage = lazy(() => import('./pages/DemoPage'));
const HomePage = lazy(() => import('./pages/HomePage'));
const ScanPage = lazy(() => import('./pages/ScanPage'));
const MapPage = lazy(() => import('./pages/MapPage'));
const ShopPage = lazy(() => import('./pages/ShopPage'));
const VolunteerPage = lazy(() => import('./pages/VolunteerPage'));
const CommunityPage = lazy(() => import('./pages/CommunityPage'));
const ProfilePage = lazy(() => import('./pages/ProfilePage'));
const AssistantPage = lazy(() => import('./pages/AssistantPage'));
const LeaderboardPage = lazy(() => import('./pages/LeaderboardPage'));
const CollectionPage = lazy(() => import('./pages/CollectionPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const DashboardPage = lazy(() => import('./pages/dispatcher/DashboardPage'));
const DispatcherMapPage = lazy(() => import('./pages/dispatcher/DispatcherMapPage'));
const AlertsPage = lazy(() => import('./pages/dispatcher/AlertsPage'));
const DevicesPage = lazy(() => import('./pages/dispatcher/DevicesPage'));
const VolunteerTasksPage = lazy(() => import('./pages/dispatcher/VolunteerTasksPage'));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <LocaleThemeProvider>
        <Toaster richColors closeButton position="top-right" />
        <AuthProvider>
          <BrowserRouter>
            <Suspense fallback={<div className="min-h-screen bg-background text-foreground flex items-center justify-center"><div className="w-9 h-9 border-4 border-primary/20 border-t-primary rounded-full animate-spin" aria-label="Загрузка страницы" /></div>}>
            <Routes>
              <Route path="/demo" element={<DemoPage />} />
              
              {/* User & Volunteer Routes */}
              <Route element={<ProtectedRoute allowedRoles={['user', 'volunteer']} />}>
                <Route element={<AppLayout />}>
                  <Route path="/" element={<Navigate to="/home" replace />} />
                  <Route path="/home" element={<HomePage />} />
                  <Route path="/scan" element={<ScanPage />} />
                  <Route path="/map" element={<MapPage />} />
                  <Route path="/shop" element={<ShopPage />} />
                  <Route path="/volunteer" element={<VolunteerPage />} />
                  <Route path="/community" element={<CommunityPage />} />
                  <Route path="/profile" element={<ProfilePage />} />
                  <Route path="/assistant" element={<AssistantPage />} />
                  <Route path="/leaderboard" element={<LeaderboardPage />} />
                  <Route path="/collection" element={<CollectionPage />} />
                  <Route path="/settings" element={<SettingsPage />} />
                </Route>
              </Route>

              {/* Dispatcher Routes */}
              <Route element={<ProtectedRoute allowedRoles={['dispatcher']} />}>
                <Route path="/dispatcher" element={<DispatcherKeyGate><DispatcherLayout /></DispatcherKeyGate>}>
                  <Route index element={<DashboardPage />} />
                  <Route path="map" element={<DispatcherMapPage />} />
                  <Route path="alerts" element={<AlertsPage />} />
                  <Route path="devices" element={<DevicesPage />} />
                  <Route path="volunteer" element={<VolunteerTasksPage />} />
                  <Route path="settings" element={<SettingsPage />} />
                </Route>
              </Route>

              <Route path="*" element={<Navigate to="/demo" replace />} />
            </Routes>
            </Suspense>
          </BrowserRouter>
        </AuthProvider>
      </LocaleThemeProvider>
    </QueryClientProvider>
  );
}
