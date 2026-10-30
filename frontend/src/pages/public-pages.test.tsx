import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { LandingPage } from '@/pages/landing-page'
import PrivacyPolicyPage from '@/pages/legal/privacy-policy-page'
import TermsPage from '@/pages/legal/terms-page'
import { NotFoundPage } from '@/pages/not-found-page'
import { expectNoA11yViolations } from '@/test/a11y'
import { renderWithProviders, signedInSession } from '@/test/render'

describe('public pages', () => {
  it('presents the landing page and accessible calls to action', async () => {
    const { container } = renderWithProviders(<LandingPage />)

    expect(
      screen.getByRole('heading', { level: 1, name: /every celebration/i }),
    ).toBeInTheDocument()
    const startLinks = screen.getAllByRole('link', { name: /start planning/i })
    expect(startLinks).toHaveLength(2)
    for (const link of startLinks) expect(link).toHaveAttribute('href', '/sign-up')
    expect(screen.getByRole('link', { name: /see how it works/i })).toBeInTheDocument()
    await expectNoA11yViolations(container)
  })

  it('sends signed-in visitors straight to their workspace', () => {
    renderWithProviders(<LandingPage />, { auth: { session: signedInSession } })

    const workspaceLinks = screen.getAllByRole('link', { name: /open your workspace/i })
    expect(workspaceLinks).toHaveLength(2)
    for (const link of workspaceLinks) expect(link).toHaveAttribute('href', '/app')
  })

  it('offers the correct recovery links on a missing page', async () => {
    const { container, unmount } = renderWithProviders(<NotFoundPage />)

    expect(
      screen.getByRole('heading', { name: 'This page is not part of the plan' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /back to festivo/i })).toHaveAttribute(
      'href',
      '/',
    )
    await expectNoA11yViolations(container)
    unmount()

    renderWithProviders(<NotFoundPage />, { auth: { session: signedInSession } })
    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute('href', '/app')
    expect(screen.getByRole('link', { name: 'Events' })).toHaveAttribute(
      'href',
      '/app/events',
    )
  })

  it('renders the legal pages with a single main heading', async () => {
    const privacy = renderWithProviders(<PrivacyPolicyPage />)
    expect(
      screen.getByRole('heading', { level: 1, name: 'Privacy Policy' }),
    ).toBeInTheDocument()
    await expectNoA11yViolations(privacy.container)
    privacy.unmount()

    const terms = renderWithProviders(<TermsPage />)
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
    await expectNoA11yViolations(terms.container)
  })
})
