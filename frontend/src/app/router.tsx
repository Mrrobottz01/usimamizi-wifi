import { createBrowserRouter, Navigate } from 'react-router-dom';
import { ProtectedRoute } from '../features/auth/ProtectedRoute';
import { LoginPage } from '../features/auth/LoginPage';
import { AppShell } from '../components/layout/AppShell';
import { SettingsLayout } from '../features/settings/SettingsLayout';
import { SMSHistoryPage } from '../features/notifications/SMSHistoryPage';
import { PlansListPage } from '../features/plans/PlansListPage';
import { VoucherBatchesListPage } from '../features/vouchers/VoucherBatchesListPage';
import { VoucherBatchDetailView } from '../features/vouchers/VoucherBatchDetailView';
import { EntitlementsListPage } from '../features/entitlements/EntitlementsListPage';
import { ActiveSessionsPage } from '../features/sessions/ActiveSessionsPage';
import { CaptivePortalPage } from '../features/portal/CaptivePortalPage';
import { CustomerPortalPage } from '../features/portal/CustomerPortalPage';
import { CustomersListPage } from '../features/customers/CustomersListPage';
import { CustomerDetailPage } from '../features/customers/CustomerDetailPage';
import { SubscriptionsListPage } from '../features/subscriptions/SubscriptionsListPage';
import { PaymentsPage } from '../features/payments/PaymentsPage';
import { WalledGardenPage } from '../features/payments/WalledGardenPage';
import { PlaceholderPage } from '../features/placeholder/PlaceholderPage';

// Infrastructure Fleet Workspaces
import { LocationsListPage } from '../features/locations/LocationsListPage';
import { LocationDetailPage } from '../features/locations/LocationDetailPage';
import { RoutersListPage } from '../features/routers/RoutersListPage';
import { RouterDetailPage } from '../features/routers/RouterDetailPage';
import { HotspotsListPage } from '../features/hotspots/HotspotsListPage';
import { HotspotDetailPage } from '../features/hotspots/HotspotDetailPage';

import { BarChart3 } from 'lucide-react';

export const router = createBrowserRouter([
  // Public Captive Portal Customer Routes (Unauthenticated, Mobile-first)
  {
    path: '/p/:slug',
    element: <CaptivePortalPage />,
  },
  {
    path: '/p/:slug/account',
    element: <CustomerPortalPage />,
  },
  {
    path: '/portal/:slug',
    element: <CaptivePortalPage />,
  },
  {
    path: '/portal/:slug/account',
    element: <CustomerPortalPage />,
  },

  // Authentication & Core Admin Shell
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AppShell>
          <Navigate to="/plans" replace />
        </AppShell>
      </ProtectedRoute>
    ),
  },

  // NETWORK INFRASTRUCTURE
  {
    path: '/locations',
    element: (
      <ProtectedRoute>
        <AppShell>
          <LocationsListPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/locations/:id',
    element: (
      <ProtectedRoute>
        <AppShell>
          <LocationDetailPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/routers',
    element: (
      <ProtectedRoute>
        <AppShell>
          <RoutersListPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/routers/:id',
    element: (
      <ProtectedRoute>
        <AppShell>
          <RouterDetailPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/hotspots',
    element: (
      <ProtectedRoute>
        <AppShell>
          <HotspotsListPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/hotspots/:id',
    element: (
      <ProtectedRoute>
        <AppShell>
          <HotspotDetailPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },

  // Compatibility redirect for old /settings/hotspot
  {
    path: '/settings/hotspot',
    element: (
      <ProtectedRoute>
        <AppShell>
          <Navigate to="/hotspots" replace />
        </AppShell>
      </ProtectedRoute>
    ),
  },

  // SYSTEM & SETTINGS
  {
    path: '/settings',
    element: (
      <ProtectedRoute>
        <AppShell>
          <SettingsLayout />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/notifications/sms-history',
    element: (
      <ProtectedRoute>
        <AppShell>
          <SMSHistoryPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/sms-history',
    element: (
      <ProtectedRoute>
        <AppShell>
          <SMSHistoryPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },

  // BILLING & ACCESS
  {
    path: '/payments',
    element: (
      <ProtectedRoute>
        <AppShell>
          <PaymentsPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/walled-garden',
    element: (
      <ProtectedRoute>
        <AppShell>
          <WalledGardenPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/plans',
    element: (
      <ProtectedRoute>
        <AppShell>
          <PlansListPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/vouchers',
    element: (
      <ProtectedRoute>
        <AppShell>
          <VoucherBatchesListPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/vouchers/batches/:id',
    element: (
      <ProtectedRoute>
        <AppShell>
          <VoucherBatchDetailView />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/entitlements',
    element: (
      <ProtectedRoute>
        <AppShell>
          <EntitlementsListPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/entitlements/:id',
    element: (
      <ProtectedRoute>
        <AppShell>
          <EntitlementsListPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },

  // OPERATIONS
  {
    path: '/sessions',
    element: (
      <ProtectedRoute>
        <AppShell>
          <ActiveSessionsPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/customers',
    element: (
      <ProtectedRoute>
        <AppShell>
          <CustomersListPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/customers/:id',
    element: (
      <ProtectedRoute>
        <AppShell>
          <CustomerDetailPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },
  {
    path: '/subscriptions',
    element: (
      <ProtectedRoute>
        <AppShell>
          <SubscriptionsListPage />
        </AppShell>
      </ProtectedRoute>
    ),
  },

  // REPORTS
  {
    path: '/reports',
    element: (
      <ProtectedRoute>
        <AppShell>
          <PlaceholderPage
            title="Analytics & Financial Reports"
            description="View revenue by plan, location, payment provider, and network usage trends."
            phase="Phase 8 Analytics"
            icon={BarChart3}
          />
        </AppShell>
      </ProtectedRoute>
    ),
  },
]);
