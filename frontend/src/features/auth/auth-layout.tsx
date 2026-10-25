import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, Check, ShieldCheck, Sparkles } from 'lucide-react'

import { Brand } from '@/components/layout/brand'

export function AuthLayout({
  title,
  description,
  children,
  footer,
}: {
  title: string
  description: string
  children: ReactNode
  footer?: ReactNode
}) {
  return (
    <div className="grid min-h-screen bg-canvas lg:grid-cols-[1fr_1.05fr]">
      <div className="flex flex-col px-4 py-6 sm:px-8 lg:px-12">
        <div className="flex items-center justify-between">
          <Brand />
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-sm text-muted transition-colors hover:text-ink"
          >
            <ArrowLeft className="size-3.5" aria-hidden="true" />
            Home
          </Link>
        </div>
        <main id="main-content" className="flex flex-1 items-center justify-center py-10">
          <div className="w-full max-w-md">
            <p className="eyebrow">Your planning workspace</p>
            <h1 className="mt-2 font-display text-3xl tracking-[-0.02em] text-ink sm:text-4xl">
              {title}
            </h1>
            <p className="mt-3 text-sm leading-6 text-muted">{description}</p>
            <div className="mt-8">{children}</div>
            {footer ? <div className="mt-6 text-sm text-muted">{footer}</div> : null}
          </div>
        </main>
        <p className="text-xs text-muted">
          © {new Date().getFullYear()} Festivo AI · Human-approved planning
        </p>
      </div>

      <aside className="relative hidden overflow-hidden border-l border-line bg-surface lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(90,73,214,0.13),transparent_60%)]"
          aria-hidden="true"
        />
        <div className="relative">
          <span className="inline-flex size-11 items-center justify-center rounded-full bg-primary-soft text-primary">
            <Sparkles className="size-5" aria-hidden="true" />
          </span>
          <blockquote className="mt-8 max-w-md font-display text-3xl leading-snug tracking-[-0.01em] text-ink">
            “The plan should feel like a place to think, not another inbox to manage.”
          </blockquote>
          <p className="mt-4 text-sm text-muted">The principle behind Festivo.</p>
        </div>
        <div className="relative space-y-4">
          {[
            'One private workspace per celebration.',
            'Budget totals calculated by the server, not guessed in the browser.',
            'AI ideas stay drafts until you choose to act on them.',
          ].map((item) => (
            <div key={item} className="flex items-start gap-3 rounded-md bg-canvas/80 p-4">
              <Check className="mt-0.5 size-4 shrink-0 text-success" aria-hidden="true" />
              <p className="text-sm leading-6 text-ink-soft">{item}</p>
            </div>
          ))}
          <p className="flex items-center gap-2 pt-2 text-xs text-muted">
            <ShieldCheck className="size-3.5" aria-hidden="true" />
            Festivo never books vendors or spends money on your behalf.
          </p>
        </div>
      </aside>
    </div>
  )
}
