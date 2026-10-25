import { createBrowserRouter, type RouteObject } from 'react-router-dom'

import { AppShell } from '@/components/layout/app-shell'
import { EventLayout } from '@/components/layout/event-layout'
import { PublicLayout } from '@/components/layout/public-layout'
import { ProtectedRoute, PublicOnlyRoute } from '@/features/auth/auth-guard'
import { AiPlanPage } from '@/pages/events/ai-plan-page'
import { AuthCallbackPage } from '@/pages/auth/auth-callback-page'
import { BudgetPage } from '@/pages/events/budget-page'
import { DashboardPage } from '@/pages/dashboard-page'
import { EventCreatePage, EventEditPage } from '@/pages/events/event-form-page'
import { EventOverviewPage } from '@/pages/events/event-overview-page'
import { EventsListPage } from '@/pages/events/events-list-page'
import { ExportsPage } from '@/pages/events/exports-page'
import { ForgotPasswordPage } from '@/pages/auth/forgot-password-page'
import { LandingPage } from '@/pages/landing-page'
import { NotFoundPage } from '@/pages/not-found-page'
import { ProposalsPage } from '@/pages/events/proposals-page'
import { ResetPasswordPage } from '@/pages/auth/reset-password-page'
import { SettingsPage } from '@/pages/settings-page'
import { SignInPage } from '@/pages/auth/sign-in-page'
import { SignUpPage } from '@/pages/auth/sign-up-page'
import { TimelinePage } from '@/pages/events/timeline-page'
import { VendorComparePage } from '@/pages/events/vendor-compare-page'
import { VendorsPage } from '@/pages/events/vendors-page'

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <PublicLayout />,
    children: [
      { index: true, element: <LandingPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
  {
    path: '/sign-in',
    element: (
      <PublicOnlyRoute>
        <SignInPage />
      </PublicOnlyRoute>
    ),
  },
  {
    path: '/sign-up',
    element: (
      <PublicOnlyRoute>
        <SignUpPage />
      </PublicOnlyRoute>
    ),
  },
  {
    path: '/forgot-password',
    element: (
      <PublicOnlyRoute>
        <ForgotPasswordPage />
      </PublicOnlyRoute>
    ),
  },
  { path: '/reset-password', element: <ResetPasswordPage /> },
  { path: '/auth/callback', element: <AuthCallbackPage /> },
  {
    path: '/app',
    element: (
      <ProtectedRoute>
        <AppShell />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'events', element: <EventsListPage /> },
      { path: 'events/new', element: <EventCreatePage /> },
      {
        path: 'events/:eventId',
        element: <EventLayout />,
        children: [
          { index: true, element: <EventOverviewPage /> },
          { path: 'edit', element: <EventEditPage /> },
          { path: 'budget', element: <BudgetPage /> },
          { path: 'timeline', element: <TimelinePage /> },
          { path: 'vendors', element: <VendorsPage /> },
          { path: 'vendors/compare', element: <VendorComparePage /> },
          { path: 'ai-plan', element: <AiPlanPage /> },
          { path: 'proposals', element: <ProposalsPage /> },
          { path: 'exports', element: <ExportsPage /> },
          { path: '*', element: <NotFoundPage /> },
        ],
      },
      { path: 'settings', element: <SettingsPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]

export const router = createBrowserRouter(routes)
