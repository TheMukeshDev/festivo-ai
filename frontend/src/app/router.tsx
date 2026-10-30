import { createBrowserRouter, type RouteObject } from 'react-router-dom'
import { lazy, Suspense } from 'react'

import { AppShell } from '@/components/layout/app-shell'
import { EventLayout } from '@/components/layout/event-layout'
import { PublicLayout } from '@/components/layout/public-layout'
import { ProtectedRoute, PublicOnlyRoute } from '@/features/auth/auth-guard'
import { LandingPage } from '@/pages/landing-page'
import { NotFoundPage } from '@/pages/not-found-page'
import PrivacyPolicyPage from '@/pages/legal/privacy-policy-page'
import TermsPage from '@/pages/legal/terms-page'

const withSuspense = (Component: React.LazyExoticComponent<React.ComponentType>) => (
  <Suspense fallback={<div className="p-8 text-center">Loading...</div>}>
    <Component />
  </Suspense>
)

const AiPlanPage = lazy(() =>
  import('@/pages/events/ai-plan-page').then((m) => ({ default: m.AiPlanPage })),
)
const AuthCallbackPage = lazy(() =>
  import('@/pages/auth/auth-callback-page').then((m) => ({ default: m.AuthCallbackPage })),
)
const BudgetPage = lazy(() =>
  import('@/pages/events/budget-page').then((m) => ({ default: m.BudgetPage })),
)
const DashboardPage = lazy(() =>
  import('@/pages/dashboard-page').then((m) => ({ default: m.DashboardPage })),
)
const EventCreatePage = lazy(() =>
  import('@/pages/events/event-form-page').then((m) => ({ default: m.EventCreatePage })),
)
const EventEditPage = lazy(() =>
  import('@/pages/events/event-form-page').then((m) => ({ default: m.EventEditPage })),
)
const EventOverviewPage = lazy(() =>
  import('@/pages/events/event-overview-page').then((m) => ({
    default: m.EventOverviewPage,
  })),
)
const EventsListPage = lazy(() =>
  import('@/pages/events/events-list-page').then((m) => ({ default: m.EventsListPage })),
)
const ExportsPage = lazy(() =>
  import('@/pages/events/exports-page').then((m) => ({ default: m.ExportsPage })),
)
const ForgotPasswordPage = lazy(() =>
  import('@/pages/auth/forgot-password-page').then((m) => ({
    default: m.ForgotPasswordPage,
  })),
)
const ProposalsPage = lazy(() =>
  import('@/pages/events/proposals-page').then((m) => ({ default: m.ProposalsPage })),
)
const ResetPasswordPage = lazy(() =>
  import('@/pages/auth/reset-password-page').then((m) => ({
    default: m.ResetPasswordPage,
  })),
)
const SettingsPage = lazy(() =>
  import('@/pages/settings-page').then((m) => ({ default: m.SettingsPage })),
)
const SignInPage = lazy(() =>
  import('@/pages/auth/sign-in-page').then((m) => ({ default: m.SignInPage })),
)
const SignUpPage = lazy(() =>
  import('@/pages/auth/sign-up-page').then((m) => ({ default: m.SignUpPage })),
)
const TimelinePage = lazy(() =>
  import('@/pages/events/timeline-page').then((m) => ({ default: m.TimelinePage })),
)
const VendorComparePage = lazy(() =>
  import('@/pages/events/vendor-compare-page').then((m) => ({
    default: m.VendorComparePage,
  })),
)
const VendorsPage = lazy(() =>
  import('@/pages/events/vendors-page').then((m) => ({ default: m.VendorsPage })),
)

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <PublicLayout />,
    children: [
      { index: true, element: <LandingPage /> },
      {
        path: 'privacy',
        element: withSuspense(lazy(() => Promise.resolve({ default: PrivacyPolicyPage }))),
      },
      {
        path: 'terms',
        element: withSuspense(lazy(() => Promise.resolve({ default: TermsPage }))),
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
  {
    path: '/sign-in',
    element: <PublicOnlyRoute>{withSuspense(SignInPage)}</PublicOnlyRoute>,
  },
  {
    path: '/sign-up',
    element: <PublicOnlyRoute>{withSuspense(SignUpPage)}</PublicOnlyRoute>,
  },
  {
    path: '/forgot-password',
    element: <PublicOnlyRoute>{withSuspense(ForgotPasswordPage)}</PublicOnlyRoute>,
  },
  { path: '/reset-password', element: withSuspense(ResetPasswordPage) },
  { path: '/auth/callback', element: withSuspense(AuthCallbackPage) },
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
