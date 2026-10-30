import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import {
  AlertTriangle,
  Bot,
  CircleDollarSign,
  Clock3,
  ListChecks,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  Store,
  WandSparkles,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { ErrorState } from '@/components/ui/error-state'
import { FormField } from '@/components/ui/form-field'
import { PageSkeleton } from '@/components/ui/skeleton'
import { useAiStatusQuery, useEventQuery } from '@/features/events/queries'
import { aiPlanningApi } from '@/lib/api/queries'
import { formatDateTime, formatMoney } from '@/lib/format'
import { AI_PRIORITY_LABELS, BUDGET_SOURCE_LABELS } from '@/lib/labels'
import { cn } from '@/lib/utils'
import type {
  AiPlanRequest,
  AiPlanResponse,
  AiPriority,
  AiTaskSuggestion,
  ConversationMessage,
  ProposalRecord,
} from '@/types/api'

const focusOptions = [
  { value: 'budget', label: 'Budget allocation' },
  { value: 'timeline', label: 'Timeline and deadlines' },
  { value: 'vendors', label: 'Vendor categories' },
  { value: 'tasks', label: 'Task planning' },
  { value: 'theme', label: 'Theme and atmosphere' },
  { value: 'guest_experience', label: 'Guest experience' },
  { value: 'risks', label: 'Risks and constraints' },
]

const priorityTone: Record<AiPriority, 'neutral' | 'info' | 'warning' | 'danger'> = {
  low: 'neutral',
  medium: 'info',
  high: 'warning',
  critical: 'danger',
}

const configurationLabels: Record<string, string> = {
  disabled: 'AI planning is disabled',
  incomplete: 'AI provider configuration is incomplete',
  configured: 'AI provider configured',
}

function parsePreferences(value: string): Record<string, unknown> {
  const entries: [string, string][] = []
  value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(0, 20)
    .forEach((line, index) => {
      const separator = line.indexOf(':')
      if (separator > 0 && separator < line.length - 1) {
        const key = line.slice(0, separator).trim()
        const parsed = line.slice(separator + 1).trim()
        if (key && parsed) {
          entries.push([key, parsed])
          return
        }
      }
      entries.push([`preference_${index + 1}`, line])
    })
  return Object.fromEntries(entries)
}

function normalizePlanResponse(response: AiPlanResponse | ProposalRecord): AiPlanResponse {
  const candidate = (
    'ai_plan' in response && response.ai_plan ? response.ai_plan : response
  ) as AiPlanResponse & {
    created_at?: string
    proposal_type?: string
  }

  return {
    event_id: candidate.event_id,
    summary: candidate.summary,
    theme_ideas: candidate.theme_ideas ?? [],
    recommendations: candidate.recommendations ?? [],
    budget_suggestions: candidate.budget_suggestions ?? [],
    timeline_suggestions: candidate.timeline_suggestions ?? [],
    task_suggestions: candidate.task_suggestions ?? [],
    vendor_category_suggestions: candidate.vendor_category_suggestions ?? [],
    risks_and_constraints: candidate.risks_and_constraints ?? [],
    assumptions: candidate.assumptions ?? [],
    next_steps: candidate.next_steps ?? [],
    generated_at:
      candidate.generated_at ?? candidate.created_at ?? new Date().toISOString(),
    model_used: candidate.model_used ?? candidate.proposal_type ?? 'Gemini',
  }
}

function SectionList({
  title,
  items,
  icon: Icon,
}: {
  title: string
  items: string[]
  icon: typeof Sparkles
}) {
  if (items.length === 0) return null
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon className="size-4 text-primary" aria-hidden="true" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {items.map((item) => (
            <li
              key={item}
              className="flex items-start gap-2 text-sm leading-6 text-ink-soft"
            >
              <span
                className="mt-2 size-1.5 shrink-0 rounded-full bg-primary/60"
                aria-hidden="true"
              />
              {item}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}

function TaskSuggestion({ suggestion }: { suggestion: AiTaskSuggestion }) {
  return (
    <li className="rounded-md border border-line bg-surface-raised p-3.5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="text-sm font-semibold text-ink">{suggestion.title}</p>
        <Badge tone={priorityTone[suggestion.priority]}>
          {AI_PRIORITY_LABELS[suggestion.priority] ?? suggestion.priority}
        </Badge>
      </div>
      <p className="mt-1 text-xs leading-5 text-ink-soft">{suggestion.explanation}</p>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[0.68rem] text-muted">
        {suggestion.category ? <span>Category: {suggestion.category}</span> : null}
        {suggestion.suggested_timing ? (
          <span>Timing: {suggestion.suggested_timing}</span>
        ) : null}
        {suggestion.relative_deadline ? (
          <span>Deadline: {suggestion.relative_deadline}</span>
        ) : null}
      </div>
    </li>
  )
}

function PlanResults({
  result,
  eventCurrency,
}: {
  result: AiPlanResponse
  eventCurrency: string
}) {
  return (
    <div className="space-y-5" aria-live="polite">
      <div className="rounded-lg border border-primary/25 bg-primary-soft/40 p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <Badge tone="primary">
            <Sparkles className="size-3" aria-hidden="true" />
            Planning suggestions
          </Badge>
          <p className="text-[0.68rem] text-muted">
            {result.model_used} · {formatDateTime(result.generated_at)}
          </p>
        </div>
        <p className="mt-3 text-sm leading-7 text-ink-soft">{result.summary}</p>
        <p className="mt-3 text-xs leading-5 text-muted">
          These suggestions are not saved and are not applied to your budget, timeline,
          tasks, or vendors. Review every item before using it.
        </p>
      </div>

      {result.theme_ideas.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <WandSparkles className="size-4 text-primary" aria-hidden="true" />
              Theme ideas
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {result.theme_ideas.map((idea) => (
                <span
                  key={idea}
                  className="rounded-full border border-primary/20 bg-primary-soft/50 px-3 py-1.5 text-xs text-ink-soft"
                >
                  {idea}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      ) : null}

      {result.recommendations.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ListChecks className="size-4 text-primary" aria-hidden="true" />
              Recommendations
            </CardTitle>
            <CardDescription>
              Ideas to consider. Verify details with venues and vendors before committing.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="grid gap-3 md:grid-cols-2">
              {result.recommendations.map((recommendation) => (
                <li
                  key={`${recommendation.category}-${recommendation.description}`}
                  className="rounded-md border border-line bg-surface-raised p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm font-semibold text-ink">
                      {recommendation.category}
                    </p>
                    <Badge tone={priorityTone[recommendation.priority]}>
                      {AI_PRIORITY_LABELS[recommendation.priority] ??
                        recommendation.priority}
                    </Badge>
                  </div>
                  <p className="mt-1 text-sm leading-6 text-ink-soft">
                    {recommendation.description}
                  </p>
                  <p className="mt-2 text-xs leading-5 text-muted">
                    {recommendation.rationale}
                  </p>
                  {recommendation.assumptions.length > 0 ? (
                    <p className="mt-2 text-[0.68rem] leading-4 text-muted">
                      Assumes: {recommendation.assumptions.join(' · ')}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      {result.budget_suggestions.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <CircleDollarSign className="size-4 text-primary" aria-hidden="true" />
              Budget suggestions
            </CardTitle>
            <CardDescription>
              Suggestions are not expenses. Sources show how each estimate was formed.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {result.budget_suggestions.map((suggestion) => (
                <li
                  key={`${suggestion.category}-${suggestion.description}`}
                  className="rounded-md border border-line p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-ink">
                        {suggestion.category}
                      </p>
                      <p className="mt-0.5 text-xs text-muted">{suggestion.description}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-display text-xl text-ink">
                        {suggestion.suggested_amount
                          ? formatMoney(
                              suggestion.suggested_amount,
                              suggestion.currency || eventCurrency,
                            )
                          : 'No amount suggested'}
                      </p>
                      <Badge
                        tone={suggestion.exceeds_available ? 'warning' : 'neutral'}
                        className="mt-1"
                      >
                        {BUDGET_SOURCE_LABELS[suggestion.source] ?? suggestion.source}
                      </Badge>
                    </div>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-ink-soft">
                    {suggestion.rationale}
                  </p>
                  {suggestion.exceeds_available ? (
                    <p className="mt-2 flex items-start gap-1.5 text-xs leading-5 text-warning-strong">
                      <AlertTriangle
                        className="mt-0.5 size-3 shrink-0"
                        aria-hidden="true"
                      />
                      This suggestion may exceed the amount currently available for
                      planning.
                    </p>
                  ) : null}
                  {suggestion.assumptions.length > 0 ? (
                    <p className="mt-2 text-[0.68rem] leading-4 text-muted">
                      Assumes: {suggestion.assumptions.join(' · ')}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      {result.task_suggestions.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Clock3 className="size-4 text-primary" aria-hidden="true" />
              Tasks to consider
            </CardTitle>
            <CardDescription>
              These are suggestions only. Add them to your timeline manually if useful.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {result.task_suggestions.map((suggestion) => (
                <TaskSuggestion
                  key={`${suggestion.title}-${suggestion.category ?? ''}`}
                  suggestion={suggestion}
                />
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      {result.vendor_category_suggestions.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Store className="size-4 text-primary" aria-hidden="true" />
              Vendor categories to explore
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {result.vendor_category_suggestions.map((suggestion) => (
                <li
                  key={`${suggestion.category}-${suggestion.rationale}`}
                  className="flex items-start justify-between gap-3 rounded-md border border-line p-3"
                >
                  <div>
                    <p className="text-sm font-medium text-ink">{suggestion.category}</p>
                    <p className="mt-0.5 text-xs leading-5 text-muted">
                      {suggestion.rationale}
                    </p>
                    {suggestion.notes ? (
                      <p className="mt-1 text-[0.68rem] text-muted">{suggestion.notes}</p>
                    ) : null}
                  </div>
                  <Badge tone={priorityTone[suggestion.priority]}>
                    {AI_PRIORITY_LABELS[suggestion.priority] ?? suggestion.priority}
                  </Badge>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        <SectionList
          title="Timeline notes"
          items={result.timeline_suggestions}
          icon={Clock3}
        />
        <SectionList
          title="Risks and constraints"
          items={result.risks_and_constraints}
          icon={ShieldAlert}
        />
        <SectionList title="Assumptions" items={result.assumptions} icon={AlertTriangle} />
        <SectionList title="Next steps" items={result.next_steps} icon={ListChecks} />
      </div>
    </div>
  )
}

function readStoredConversation(eventId: string): ConversationMessage[] {
  const key = `festivo-ai-conversation:${eventId}`
  try {
    const stored = sessionStorage.getItem(key)
    if (!stored) return []
    const parsed = JSON.parse(stored) as unknown
    if (!Array.isArray(parsed)) {
      sessionStorage.removeItem(key)
      return []
    }
    return (parsed as ConversationMessage[]).slice(-12)
  } catch {
    sessionStorage.removeItem(key)
    return []
  }
}

function AiPlanContent({ eventId }: { eventId: string }) {
  const eventQuery = useEventQuery(eventId)
  const statusQuery = useAiStatusQuery(eventId)
  const [focusAreas, setFocusAreas] = useState<string[]>([])
  const [preferences, setPreferences] = useState('')
  const [notes, setNotes] = useState('')
  const [question, setQuestion] = useState('')
  const [conversation, setConversation] = useState<ConversationMessage[]>(() =>
    readStoredConversation(eventId),
  )

  useEffect(() => {
    if (conversation.length) {
      sessionStorage.setItem(
        `festivo-ai-conversation:${eventId}`,
        JSON.stringify(conversation.slice(-12)),
      )
    }
  }, [conversation, eventId])
  const [validationError, setValidationError] = useState<string | null>(null)
  const [result, setResult] = useState<AiPlanResponse | null>(null)

  const generateMutation = useMutation({
    mutationFn: (payload: AiPlanRequest) => aiPlanningApi.generate(eventId, payload),
  })
  const refineMutation = useMutation({
    mutationFn: (payload: AiPlanRequest) => aiPlanningApi.refine(eventId, payload),
  })

  const busy = generateMutation.isPending || refineMutation.isPending
  const status = statusQuery.data
  const available = Boolean(status?.enabled) && status?.configuration_state === 'configured'

  function toggleFocus(value: string) {
    setValidationError(null)
    setFocusAreas((current) =>
      current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value],
    )
  }

  async function handleSubmit() {
    setValidationError(null)
    if (focusAreas.length === 0) {
      setValidationError('Choose at least one focus area for the plan.')
      return
    }
    if (preferences.length > 4000 || notes.length > 2000) {
      setValidationError('Keep preferences under 4,000 characters and notes under 2,000.')
      return
    }

    const payload: AiPlanRequest = {
      preferences: parsePreferences(preferences),
      focus_areas: focusAreas,
      ...(notes.trim() ? { additional_notes: notes.trim() } : {}),
      ...(question.trim()
        ? {
            conversation: [
              ...conversation,
              { role: 'user' as const, content: question.trim() },
            ].slice(-12),
          }
        : conversation.length
          ? { conversation: conversation.slice(-12) }
          : {}),
    }

    try {
      const response = result
        ? await refineMutation.mutateAsync(payload)
        : await generateMutation.mutateAsync(payload)
      const normalized = normalizePlanResponse(response)
      setResult(normalized)
      if (question.trim()) {
        setConversation((current) =>
          [
            ...current,
            { role: 'user' as const, content: question.trim() },
            { role: 'assistant' as const, content: normalized.summary },
          ].slice(-12),
        )
        setQuestion('')
      }
    } catch (error) {
      setValidationError(
        error instanceof Error
          ? error.message
          : 'The AI plan could not be generated. Try again.',
      )
    }
  }

  if (statusQuery.isLoading) return <PageSkeleton />

  if (statusQuery.isError) {
    return (
      <ErrorState
        title="AI planning status could not load"
        error={statusQuery.error}
        onRetry={() => void statusQuery.refetch()}
      />
    )
  }

  if (!status) return null

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-primary/15 bg-gradient-to-br from-primary-soft/70 via-surface to-accent-soft/30 p-5 sm:p-6">
        <div className="flex items-start gap-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary text-white shadow-sm">
            <Sparkles className="size-5" aria-hidden="true" />
          </span>
          <div>
            <p className="eyebrow text-primary-strong">Draft with Gemini</p>
            <h2 className="mt-1 font-display text-2xl text-ink">AI planning</h2>
          </div>
        </div>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
          Generate planning suggestions from your event details. Nothing is saved or applied
          automatically, and AI output can be incomplete or wrong.
        </p>
      </div>

      <Card
        className={cn(available ? 'border-line' : 'border-warning/30 bg-warning-soft/40')}
      >
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle className="flex items-center gap-2 text-base">
                <Bot className="size-4 text-primary" aria-hidden="true" />
                Provider status
              </CardTitle>
              <CardDescription>
                {status.provider} ·{' '}
                {configurationLabels[status.configuration_state] ??
                  status.configuration_state}
              </CardDescription>
            </div>
            <Badge tone={available ? 'success' : 'warning'}>
              {available ? 'Ready' : 'Unavailable'}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <dl className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
            <div>
              <dt className="text-muted">Model</dt>
              <dd className="mt-0.5 font-medium text-ink">
                {status.model_configured ? 'Configured' : 'Not configured'}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Credential</dt>
              <dd className="mt-0.5 font-medium text-ink">
                {status.credential_configured ? 'Configured' : 'Not configured'}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Timeout</dt>
              <dd className="mt-0.5 font-medium text-ink">{status.timeout_seconds}s</dd>
            </div>
            <div>
              <dt className="text-muted">Retries</dt>
              <dd className="mt-0.5 font-medium text-ink">{status.max_retries}</dd>
            </div>
          </dl>
          {!available ? (
            <p className="rounded-sm bg-surface/70 p-3 text-xs leading-5 text-ink-soft">
              AI planning is not available for this workspace. Ask the administrator to
              finish configuring the AI provider, then reload this page. Your event plan can
              still be built manually.
            </p>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Guide the suggestion</CardTitle>
          <CardDescription>
            Choose what the plan should concentrate on. The AI also receives the event
            details already saved in Festivo.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="rounded-lg border border-primary/15 bg-primary-soft/35 p-4">
            <div className="flex items-start gap-3">
              <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary text-white">
                <Sparkles className="size-4" aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-ink">Ask your planning copilot</p>
                <p className="mt-1 text-xs leading-5 text-ink-soft">
                  Ask follow-up questions about the budget, timeline, vendors, or
                  priorities. Every answer creates a fresh draft for you to review.
                </p>
              </div>
            </div>
            {conversation.length ? (
              <div className="mt-4 space-y-2 border-t border-primary/10 pt-3">
                {conversation.slice(-6).map((message, index) => (
                  <div
                    key={`${message.role}-${index}`}
                    className={cn(
                      'max-w-[92%] rounded-lg px-3 py-2 text-xs leading-5',
                      message.role === 'user'
                        ? 'ml-auto bg-primary text-white'
                        : 'bg-surface text-ink-soft',
                    )}
                  >
                    {message.content}
                  </div>
                ))}
              </div>
            ) : null}
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              rows={2}
              maxLength={2000}
              disabled={!available || busy}
              placeholder="For example: Can we keep catering under 35% and move more to photography?"
              className="mt-3 flex min-h-16 w-full rounded-md border border-line-strong bg-surface px-3 py-2 text-sm text-ink shadow-inset placeholder:text-muted focus-visible:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-60"
            />
            <p className="mt-1 text-[0.68rem] text-muted">
              Follow-ups are suggestions only. Approve changes from the proposal workspace.
            </p>
          </div>

          <fieldset disabled={!available || busy}>
            <legend className="text-sm font-medium text-ink">Focus areas</legend>
            <p className="mt-1 text-xs text-muted">Choose at least one.</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {focusOptions.map((option) => {
                const checked = focusAreas.includes(option.value)
                return (
                  <label
                    key={option.value}
                    className={cn(
                      'flex cursor-pointer items-center gap-2.5 rounded-md border px-3 py-2.5 text-sm',
                      checked
                        ? 'border-primary bg-primary-soft/50 text-ink'
                        : 'border-line bg-surface-raised text-ink-soft hover:border-line-strong',
                      (!available || busy) && 'cursor-not-allowed opacity-60',
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleFocus(option.value)}
                      className="size-4 accent-primary"
                    />
                    {option.label}
                  </label>
                )
              })}
            </div>
          </fieldset>

          <FormField
            id="ai_preferences"
            label="Preferences and priorities"
            description="Optional. One item per line. Use “key: value” for a labelled preference."
          >
            <textarea
              id="ai_preferences"
              value={preferences}
              onChange={(changeEvent) => setPreferences(changeEvent.target.value)}
              rows={4}
              maxLength={4000}
              disabled={!available || busy}
              placeholder={
                'style: relaxed garden party\nMust avoid: loud music\nPriorities: good food, easy access'
              }
              className="flex min-h-24 w-full rounded-sm border border-line-strong bg-surface px-3 py-2 text-sm text-ink shadow-inset placeholder:text-muted focus-visible:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-60"
            />
          </FormField>

          <FormField
            id="ai_notes"
            label="Additional notes"
            description="Optional context that is not already captured in the event."
          >
            <textarea
              id="ai_notes"
              value={notes}
              onChange={(changeEvent) => setNotes(changeEvent.target.value)}
              rows={4}
              maxLength={2000}
              disabled={!available || busy}
              placeholder="Anything the plan should account for?"
              className="flex min-h-24 w-full rounded-sm border border-line-strong bg-surface px-3 py-2 text-sm text-ink shadow-inset placeholder:text-muted focus-visible:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-60"
            />
          </FormField>

          {validationError ? (
            <p
              role="alert"
              className="rounded-sm border border-danger/20 bg-danger-soft px-3 py-2 text-sm text-danger-strong"
            >
              {validationError}
            </p>
          ) : null}

          <div className="flex flex-col gap-3 border-t border-line pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-muted">
              AI suggestions are not verified facts. Check names, prices, and availability
              yourself.
            </p>
            <Button
              type="button"
              onClick={handleSubmit}
              disabled={!available || busy}
              className="sm:min-w-48"
            >
              {busy ? (
                <>
                  <RefreshCw className="animate-spin" aria-hidden="true" />
                  {result ? 'Refining…' : 'Generating…'}
                </>
              ) : result ? (
                <>
                  <RefreshCw aria-hidden="true" />
                  Refine suggestions
                </>
              ) : (
                <>
                  <WandSparkles aria-hidden="true" />
                  Generate suggestions
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {result ? (
        <PlanResults result={result} eventCurrency={eventQuery.data?.currency ?? 'INR'} />
      ) : null}
    </div>
  )
}

export function AiPlanPage() {
  const { eventId } = useParams()
  if (!eventId) return null
  return <AiPlanContent key={eventId} eventId={eventId} />
}
