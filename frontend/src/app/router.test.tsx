import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { AppProviders } from '@/app/providers'
import { createAppQueryClient } from '@/app/query-client'
import { routes } from '@/app/router'
import { isFirebaseConfigured } from '@/lib/env'

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  render(
    <AppProviders client={createAppQueryClient()}>
      <RouterProvider router={router} />
    </AppProviders>,
  )
  return router
}

describe('application routes', () => {
  it('renders the public not-found page for an unknown address', async () => {
    renderAt('/not-a-real-page')
    expect(
      await screen.findByRole('heading', {
        name: 'This page is not part of the plan',
      }),
    ).toBeInTheDocument()
  })

  it('renders the sign-in page for anonymous visitors', async () => {
    renderAt('/sign-in')
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
  })

  it('protects the workspace when authentication is not configured', async () => {
    if (isFirebaseConfigured) return

    renderAt('/app')
    expect(await screen.findByText('Authentication is not configured')).toBeInTheDocument()
  })
})
