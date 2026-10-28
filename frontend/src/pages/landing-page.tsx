import { Link } from 'react-router-dom'
import {
  ArrowRight,
  BadgeCheck,
  CalendarRange,
  Check,
  CircleDollarSign,
  ClipboardList,
  Compass,
  LockKeyhole,
  Sparkles,
  Store,
  Users,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/use-auth'
import { EVENT_TYPES } from '@/lib/labels'

const steps = [
  {
    icon: Compass,
    title: 'Describe the celebration',
    body: 'Add the date, guest count, budget, location, and the details that matter to you.',
  },
  {
    icon: ClipboardList,
    title: 'Shape a working plan',
    body: 'Build a decimal-safe budget, generate a timeline, and keep tasks and vendor options together.',
  },
  {
    icon: Sparkles,
    title: 'Make the decisions',
    body: 'Use AI suggestions as a starting point. You confirm what changes, what gets booked, and what gets spent.',
  },
]

const features = [
  {
    icon: CircleDollarSign,
    title: 'A budget you can trust',
    body: 'Server-calculated totals, reserve tracking, category breakdowns, and expense status from estimate to confirmed.',
  },
  {
    icon: CalendarRange,
    title: 'A timeline that adapts',
    body: 'Generate a practical checklist, then edit due dates, priorities, and status as your plans move.',
  },
  {
    icon: Store,
    title: 'Vendor decisions, side by side',
    body: 'Keep quotes and notes in one place, shortlist options, and compare only the information you actually have.',
  },
  {
    icon: Sparkles,
    title: 'Thoughtful AI suggestions',
    body: 'Ask for themes, budget ideas, and next steps grounded in your event. Suggestions stay drafts until you act.',
  },
  {
    icon: Users,
    title: 'Built for different gatherings',
    body: 'Weddings, birthdays, college fests, and community events all get a workspace shaped around their needs.',
  },
  {
    icon: BadgeCheck,
    title: 'No invented certainty',
    body: 'Missing prices, different currencies, and unverified vendors are called out instead of being filled in.',
  },
]

function ProductPreview() {
  return (
    <div className="relative mx-auto w-full max-w-xl">
      <div
        className="absolute -left-4 top-12 hidden size-24 rounded-full bg-accent-soft blur-2xl sm:block"
        aria-hidden="true"
      />
      <div
        className="absolute -right-6 bottom-8 hidden size-32 rounded-full bg-primary-soft blur-2xl sm:block"
        aria-hidden="true"
      />
      <div className="relative rounded-xl border border-line bg-surface p-3 shadow-raised sm:p-4">
        <div className="flex items-center justify-between border-b border-line px-1 pb-3">
          <div>
            <p className="text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-muted">
              Event overview
            </p>
            <p className="font-display text-lg text-ink">Ananya & Rohan</p>
          </div>
          <Badge tone="success">
            <Check className="size-3" aria-hidden="true" />
            On track
          </Badge>
        </div>
        <div className="grid gap-3 pt-3 sm:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-3">
            <div className="rounded-md border border-line bg-canvas/70 p-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-ink">Budget used</span>
                <span className="text-muted">62%</span>
              </div>
              <div className="mt-2 h-2 rounded-full bg-line">
                <div className="h-2 w-[62%] rounded-full bg-primary" />
              </div>
              <div className="mt-2 flex justify-between text-[0.68rem] text-muted">
                <span>₹4,65,000 spent</span>
                <span>₹2,85,000 left</span>
              </div>
            </div>
            <div className="rounded-md border border-line bg-surface-raised p-3">
              <p className="text-[0.65rem] font-semibold uppercase tracking-[0.1em] text-muted">
                Next up
              </p>
              <ul className="mt-2 space-y-2 text-xs text-ink-soft">
                <li className="flex items-start gap-2">
                  <span
                    className="mt-1.5 size-1.5 rounded-full bg-accent"
                    aria-hidden="true"
                  />
                  Confirm catering headcount
                </li>
                <li className="flex items-start gap-2">
                  <span
                    className="mt-1.5 size-1.5 rounded-full bg-primary"
                    aria-hidden="true"
                  />
                  Review photographer quotes
                </li>
                <li className="flex items-start gap-2">
                  <span
                    className="mt-1.5 size-1.5 rounded-full bg-line-strong"
                    aria-hidden="true"
                  />
                  Send invitations
                </li>
              </ul>
            </div>
            <div className="flex gap-2 rounded-md bg-primary-soft/70 p-3">
              <Sparkles
                className="mt-0.5 size-4 shrink-0 text-primary"
                aria-hidden="true"
              />
              <div>
                <p className="text-xs font-semibold text-primary-strong">
                  AI draft suggestion
                </p>
                <p className="mt-0.5 text-[0.7rem] leading-5 text-ink-soft">
                  A pastel garden theme could reuse the venue&apos;s existing greenery.
                </p>
              </div>
            </div>
          </div>
          <div className="space-y-3">
            <div className="rounded-md border border-line bg-surface-raised p-3">
              <p className="text-[0.65rem] font-semibold uppercase tracking-[0.1em] text-muted">
                Vendors
              </p>
              <div className="mt-2 space-y-2">
                {[
                  ['The Courtyard', 'Booked', 'success'],
                  ['Saffron Table', 'Quoted', 'warning'],
                  ['Frame & Light', 'Shortlisted', 'primary'],
                ].map(([name, status, tone]) => (
                  <div key={name} className="flex items-center justify-between gap-2">
                    <span className="truncate text-xs text-ink-soft">{name}</span>
                    <Badge tone={tone as 'success' | 'warning' | 'primary'}>{status}</Badge>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-md border border-line bg-surface-raised p-3">
              <p className="text-[0.65rem] font-semibold uppercase tracking-[0.1em] text-muted">
                Planning progress
              </p>
                <div className="mt-3 flex items-end gap-1.5" role="img" aria-label="Planning progress chart showing increasing task completion">
                {[35, 55, 48, 72, 66, 84, 76, 92].map((height, index) => (
                  <div
                    key={index}
                    className="w-full rounded-t-xs bg-primary/70"
                    style={{ height: `${height * 0.55}px` }}
                  />
                ))}
              </div>
              <p className="mt-2 text-[0.68rem] leading-5 text-muted">
                12 of 18 tasks complete
              </p>
            </div>
          </div>
        </div>
      </div>
      <p className="mt-3 text-center text-[0.68rem] text-muted">
        Illustrative product preview using sample planning data.
      </p>
    </div>
  )
}

export function LandingPage() {
  const auth = useAuth()
  const primaryTo = auth.session ? '/app' : '/sign-up'
  const primaryLabel = auth.session ? 'Open your workspace' : 'Start planning'

  return (
    <main id="main-content">
      <section className="relative overflow-hidden">
        <div
          className="pointer-events-none absolute inset-x-0 top-0 h-[32rem] bg-[radial-gradient(ellipse_at_top,rgba(90,73,214,0.1),transparent_65%)]"
          aria-hidden="true"
        />
        <div className="relative mx-auto grid max-w-7xl items-center gap-12 px-4 py-16 sm:px-6 sm:py-20 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16 lg:px-8 lg:py-24">
          <div className="max-w-2xl">
            <Badge tone="primary" className="mb-5 px-3 py-1">
              <Sparkles className="size-3" aria-hidden="true" />
              AI-assisted, human-approved
            </Badge>
            <h1 className="display-title">
              Every celebration,
              <br />
              <span className="text-primary">held together.</span>
            </h1>
            <p className="prose-copy mt-5 max-w-xl text-base sm:text-lg">
              Festivo AI brings your budget, timeline, tasks, and vendor options into one
              calm workspace — with AI suggestions that stay clearly separate from your
              decisions.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Button asChild size="lg">
                <Link to={primaryTo}>
                  {primaryLabel}
                  <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <a href="#how-it-works">See how it works</a>
              </Button>
            </div>
            <div className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted">
              <span className="inline-flex items-center gap-1.5">
                <LockKeyhole className="size-3.5" aria-hidden="true" />
                Private by default
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Check className="size-3.5" aria-hidden="true" />
                Built for four event types
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Check className="size-3.5" aria-hidden="true" />
                No fabricated vendor data
              </span>
            </div>
          </div>
          <ProductPreview />
        </div>
      </section>

      <section className="border-y border-line bg-surface" id="how-it-works">
        <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8 lg:py-20">
          <div className="max-w-2xl">
            <p className="eyebrow">How it works</p>
            <h2 className="mt-3 font-display text-3xl tracking-[-0.02em] sm:text-4xl">
              From scattered notes to a plan you can act on.
            </h2>
            <p className="prose-copy mt-4">
              Festivo keeps the financial and practical details connected, so a change to
              one part of the plan does not disappear into a chat thread.
            </p>
          </div>
          <div className="mt-10 grid gap-5 md:grid-cols-3">
            {steps.map((step, index) => (
              <div
                key={step.title}
                className="relative rounded-lg border border-line bg-canvas/60 p-6"
              >
                <span className="absolute right-5 top-5 font-display text-3xl text-muted">
                  0{index + 1}
                </span>
                <span className="flex size-10 items-center justify-center rounded-full bg-primary-soft text-primary">
                  <step.icon className="size-5" aria-hidden="true" />
                </span>
                <h3 className="mt-5 font-display text-xl text-ink">{step.title}</h3>
                <p className="mt-2 text-sm leading-6 text-muted">{step.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section
        className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8 lg:py-20"
        id="features"
      >
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <p className="eyebrow">The workspace</p>
            <h2 className="mt-3 font-display text-3xl tracking-[-0.02em] sm:text-4xl">
              Practical tools for the parts that actually matter.
            </h2>
          </div>
          <p className="max-w-md text-sm leading-6 text-muted">
            No dashboards full of invented numbers. Every summary is built from the details
            you or your vendors provide.
          </p>
        </div>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((feature) => (
            <article
              key={feature.title}
              className="surface-card p-6 transition-shadow hover:shadow-raised"
            >
              <span className="flex size-10 items-center justify-center rounded-full bg-canvas text-primary">
                <feature.icon className="size-5" aria-hidden="true" />
              </span>
              <h3 className="mt-4 font-display text-xl text-ink">{feature.title}</h3>
              <p className="mt-2 text-sm leading-6 text-muted">{feature.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-line bg-surface">
        <div className="mx-auto grid max-w-7xl gap-10 px-4 py-16 sm:px-6 lg:grid-cols-[0.8fr_1.2fr] lg:px-8 lg:py-20">
          <div>
            <p className="eyebrow">Made for real gatherings</p>
            <h2 className="mt-3 font-display text-3xl tracking-[-0.02em] sm:text-4xl">
              One planner, four different rhythms.
            </h2>
            <p className="prose-copy mt-4">
              A wedding needs a long runway and careful vendor decisions. A college fest
              needs fast task turnover and tight budgets. Festivo adapts without pretending
              they are the same.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {EVENT_TYPES.map((type) => (
              <div
                key={type.value}
                className="rounded-md border border-line bg-canvas/60 p-5"
              >
                <h3 className="font-semibold text-ink">{type.label}</h3>
                <p className="mt-1 text-sm leading-6 text-muted">{type.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section
        className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8 lg:py-20"
        id="privacy"
      >
        <div className="grid gap-10 rounded-xl border border-line bg-surface p-6 shadow-soft sm:p-10 lg:grid-cols-2">
          <div>
            <p className="eyebrow">Privacy and control</p>
            <h2 className="mt-3 font-display text-3xl tracking-[-0.02em]">
              Your plan stays yours.
            </h2>
            <p className="prose-copy mt-4">
              Your event data is private to your account. AI-generated ideas are drafts and
              are never applied automatically. Vendor costs, bookings, and payments remain
              your decisions.
            </p>
            <ul className="mt-6 space-y-3 text-sm text-ink-soft">
              {[
                'Authenticated access to every event workspace.',
                'Server-side budget calculations and validation.',
                'AI output labelled with its model and treated as untrusted text.',
                'No service-role keys, database passwords, or AI keys in the browser.',
              ].map((item) => (
                <li key={item} className="flex items-start gap-2.5">
                  <Check
                    className="mt-0.5 size-4 shrink-0 text-success"
                    aria-hidden="true"
                  />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <div className="flex flex-col justify-between rounded-lg bg-canvas p-6">
            <div>
              <LockKeyhole className="size-6 text-primary" aria-hidden="true" />
              <h3 className="mt-4 font-display text-2xl">Human approval, by design.</h3>
              <p className="mt-2 text-sm leading-6 text-muted">
                Festivo can suggest a theme, a budget range, or a next task. It does not
                contact vendors, confirm bookings, or spend money for you.
              </p>
            </div>
            <div className="mt-8">
              <Button asChild size="lg" className="w-full sm:w-auto">
                <Link to={primaryTo}>
                  {primaryLabel}
                  <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}
