import { useState } from 'react'
import { Link, Outlet } from 'react-router-dom'
import { ArrowRight, Menu } from 'lucide-react'

import { Brand } from '@/components/layout/brand'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { useAuth } from '@/features/auth/use-auth'

const navLinks = [
  { href: '/#how-it-works', label: 'How it works' },
  { href: '/#features', label: 'Features' },
  { href: '/#privacy', label: 'Privacy' },
]

export function PublicLayout() {
  const auth = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="flex min-h-screen flex-col bg-canvas">
      <a
        href="#main-content"
        className="sr-only z-[100] rounded-sm bg-primary px-4 py-2 text-white focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
      >
        Skip to main content
      </a>

      <header className="sticky top-0 z-40 border-b border-line/80 bg-canvas/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
          <Brand />
          <nav aria-label="Main navigation" className="hidden items-center gap-6 md:flex">
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="text-sm font-medium text-ink-soft transition-colors hover:text-ink"
              >
                {link.label}
              </a>
            ))}
          </nav>
          <div className="hidden items-center gap-2 md:flex">
            {auth.session ? (
              <Button asChild size="sm">
                <Link to="/app">
                  Open workspace
                  <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
            ) : (
              <>
                <Button asChild variant="ghost" size="sm">
                  <Link to="/sign-in">Sign in</Link>
                </Button>
                <Button asChild size="sm">
                  <Link to="/sign-up">Get started</Link>
                </Button>
              </>
            )}
          </div>
          <Dialog open={menuOpen} onOpenChange={setMenuOpen}>
            <DialogTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="md:hidden"
                aria-label="Open navigation menu"
              >
                <Menu aria-hidden="true" />
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-sm">
              <DialogHeader>
                <DialogTitle>Navigate Festivo</DialogTitle>
              </DialogHeader>
              <nav aria-label="Mobile navigation" className="flex flex-col gap-1">
                {navLinks.map((link) => (
                  <a
                    key={link.href}
                    href={link.href}
                    onClick={() => setMenuOpen(false)}
                    className="flex items-center justify-between rounded-sm px-3 py-3 text-sm font-medium text-ink-soft hover:bg-canvas"
                  >
                    {link.label}
                    <ArrowRight className="size-3.5 text-muted" aria-hidden="true" />
                  </a>
                ))}
              </nav>
              <div className="mt-4 grid gap-2">
                {auth.session ? (
                  <DialogClose asChild>
                    <Button asChild>
                      <Link to="/app">Open workspace</Link>
                    </Button>
                  </DialogClose>
                ) : (
                  <>
                    <DialogClose asChild>
                      <Button asChild variant="outline">
                        <Link to="/sign-in">Sign in</Link>
                      </Button>
                    </DialogClose>
                    <DialogClose asChild>
                      <Button asChild>
                        <Link to="/sign-up">Create your workspace</Link>
                      </Button>
                    </DialogClose>
                  </>
                )}
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </header>

      <main id="main-content" className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-line bg-surface">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-10 sm:px-6 lg:flex-row lg:items-start lg:justify-between lg:px-8">
          <div className="max-w-sm">
            <Brand />
            <p className="mt-3 text-sm leading-6 text-muted">
              A calmer way to plan celebrations. Keep budgets, tasks, vendors, and ideas in
              one editable workspace.
            </p>
          </div>
          <nav
            aria-label="Footer navigation"
            className="grid grid-cols-2 gap-8 text-sm sm:grid-cols-3"
          >
            <div>
              <p className="font-semibold text-ink">Product</p>
              <ul className="mt-3 space-y-2 text-muted">
                <li>
                  <a className="hover:text-ink" href="/#features">
                    Features
                  </a>
                </li>
                <li>
                  <a className="hover:text-ink" href="/#how-it-works">
                    How it works
                  </a>
                </li>
                <li>
                  <Link className="hover:text-ink" to="/sign-up">
                    Create an account
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <p className="font-semibold text-ink">Account</p>
              <ul className="mt-3 space-y-2 text-muted">
                <li>
                  <Link className="hover:text-ink" to="/sign-in">
                    Sign in
                  </Link>
                </li>
                <li>
                  <Link className="hover:text-ink" to="/forgot-password">
                    Reset password
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <p className="font-semibold text-ink">Trust</p>
              <ul className="mt-3 space-y-2 text-muted">
                <li>
                  <a className="hover:text-ink" href="/#privacy">
                    Privacy and control
                  </a>
                </li>
              </ul>
            </div>
          </nav>
        </div>
        <div className="border-t border-line/70 py-5">
          <p className="mx-auto max-w-7xl px-4 text-xs text-muted sm:px-6 lg:px-8">
            © {new Date().getFullYear()} Festivo AI. Vendor details and costs are entered by
            you; Festivo does not make bookings or verify vendors.
          </p>
        </div>
      </footer>
    </div>
  )
}
