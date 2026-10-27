import { useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  CalendarDays,
  ChevronRight,
  LayoutDashboard,
  LogOut,
  Menu,
  Plus,
  Settings,
  Sparkles,
} from 'lucide-react'
import { toast } from 'sonner'

import { Brand } from '@/components/layout/brand'
import { Button, buttonVariants } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { useAuth } from '@/features/auth/use-auth'
import { cn } from '@/lib/utils'

const navItems = [
  { to: '/app', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/app/events', label: 'Events', icon: CalendarDays, end: false },
  { to: '/app/settings', label: 'Settings', icon: Settings, end: true },
]

function navClass(isActive: boolean): string {
  return cn(
    'group flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-all',
    isActive
      ? 'bg-primary-soft text-primary-strong shadow-sm'
      : 'text-ink-soft hover:-translate-y-px hover:bg-canvas hover:text-ink',
  )
}

function NavItems({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav aria-label="Workspace navigation" className="flex flex-col gap-1">
      {navItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          onClick={onNavigate}
          className={({ isActive }) => navClass(isActive)}
        >
          <item.icon className="size-4" aria-hidden="true" />
          {item.label}
        </NavLink>
      ))}
    </nav>
  )
}

function UserPanel() {
  const auth = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [signingOut, setSigningOut] = useState(false)
  const displayName =
    (auth.user?.user_metadata.full_name as string | undefined)?.trim() ||
    auth.user?.email ||
    'Your account'

  async function handleSignOut() {
    setSigningOut(true)
    try {
      queryClient.clear()
      await auth.signOut()
      toast.success('Signed out.')
      navigate('/', { replace: true })
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not sign out.')
    } finally {
      setSigningOut(false)
    }
  }

  return (
    <div className="rounded-md border border-line bg-surface p-3">
      <div className="flex items-center gap-3">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary-soft text-sm font-semibold text-primary-strong">
          {displayName.slice(0, 1).toUpperCase()}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-ink">{displayName}</p>
          {displayName !== auth.user?.email ? (
            <p className="truncate text-xs text-muted">{auth.user?.email}</p>
          ) : null}
        </div>
      </div>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={handleSignOut}
        disabled={signingOut}
        className="mt-3 w-full justify-start"
      >
        <LogOut aria-hidden="true" />
        {signingOut ? 'Signing out…' : 'Sign out'}
      </Button>
    </div>
  )
}

function CreateEventLink({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <Link
      to="/app/events/new"
      onClick={onNavigate}
      className={cn(buttonVariants({ size: 'sm' }), 'w-full justify-start')}
    >
      <Plus aria-hidden="true" />
      Create event
    </Link>
  )
}

export function AppShell() {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="min-h-screen bg-canvas">
      <a
        href="#main-content"
        className="sr-only z-[100] rounded-sm bg-primary px-4 py-2 text-white focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
      >
        Skip to main content
      </a>

      <aside className="workspace-sidebar fixed inset-y-0 left-0 hidden w-[17rem] flex-col border-r border-line lg:flex">
        <div className="flex h-16 items-center border-b border-line px-5">
          <Brand to="/app" />
        </div>
        <div className="flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto p-4">
          <CreateEventLink />
          <NavItems />
          <div className="mt-auto space-y-3">
            <div className="rounded-lg border border-primary/10 bg-primary-soft/45 p-3">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.1em] text-muted">
                <Sparkles className="size-3.5 text-accent" aria-hidden="true" />
                Planning note
              </div>
              <p className="mt-2 text-xs leading-5 text-ink-soft">
                AI suggestions are drafts. You decide what gets applied, booked, or paid
                for.
              </p>
            </div>
            <UserPanel />
          </div>
        </div>
      </aside>

      <div className="lg:pl-[17rem]">
        <header className="sticky top-0 z-30 border-b border-line bg-canvas/90 backdrop-blur lg:hidden">
          <div className="flex h-16 items-center justify-between gap-3 px-4">
            <Brand to="/app" />
            <Dialog open={menuOpen} onOpenChange={setMenuOpen}>
              <DialogTrigger asChild>
                <Button variant="ghost" size="icon" aria-label="Open workspace menu">
                  <Menu aria-hidden="true" />
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-sm">
                <DialogHeader>
                  <DialogTitle>Festivo workspace</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <CreateEventLink onNavigate={() => setMenuOpen(false)} />
                  <NavItems onNavigate={() => setMenuOpen(false)} />
                  <UserPanel />
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </header>

        <main
          id="main-content"
          className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-8"
        >
          <Outlet />
          <div className="mt-12 flex items-center justify-between border-t border-line pt-5 text-xs text-muted">
            <span>Festivo AI · Planning workspace</span>
            <Link to="/" className="inline-flex items-center gap-1 hover:text-ink">
              About Festivo
              <ChevronRight className="size-3" aria-hidden="true" />
            </Link>
          </div>
        </main>
      </div>
    </div>
  )
}
