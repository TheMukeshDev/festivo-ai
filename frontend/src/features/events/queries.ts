import { useQuery } from '@tanstack/react-query'

import { ApiError } from '@/lib/api/errors'
import {
  aiPlanningApi,
  budgetsApi,
  eventsApi,
  queryKeys,
  timelinesApi,
  vendorsApi,
  type TaskFilters,
  type VendorFilters,
} from '@/lib/api/queries'
import type { BudgetResponse, TimelineRecord } from '@/types/api'

export function useEventsQuery() {
  return useQuery({
    queryKey: queryKeys.events,
    queryFn: () => eventsApi.list(100, 0),
  })
}

export function useEventQuery(eventId: string | undefined) {
  return useQuery({
    queryKey: eventId ? queryKeys.event(eventId) : ['events', 'missing'],
    queryFn: () => eventsApi.get(eventId!),
    enabled: Boolean(eventId),
  })
}

export function useBudgetQuery(eventId: string | undefined) {
  return useQuery({
    queryKey: eventId ? queryKeys.budget(eventId) : ['budget', 'missing'],
    queryFn: async (): Promise<BudgetResponse | null> => {
      try {
        return await budgetsApi.get(eventId!)
      } catch (error) {
        if (error instanceof ApiError && error.isNotFound) return null
        throw error
      }
    },
    enabled: Boolean(eventId),
  })
}

export function useTimelineQuery(eventId: string | undefined) {
  return useQuery({
    queryKey: eventId ? queryKeys.timeline(eventId) : ['timeline', 'missing'],
    queryFn: async (): Promise<TimelineRecord | null> => {
      try {
        return await timelinesApi.get(eventId!)
      } catch (error) {
        if (error instanceof ApiError && error.isNotFound) return null
        throw error
      }
    },
    enabled: Boolean(eventId),
  })
}

export function useTasksQuery(eventId: string | undefined, filters: TaskFilters = {}) {
  return useQuery({
    queryKey: eventId ? queryKeys.tasks(eventId, filters) : ['tasks', 'missing'],
    queryFn: () => timelinesApi.listTasks(eventId!, filters),
    enabled: Boolean(eventId),
  })
}

export function useVendorsQuery(eventId: string | undefined, filters: VendorFilters = {}) {
  return useQuery({
    queryKey: eventId ? queryKeys.vendors(eventId, filters) : ['vendors', 'missing'],
    queryFn: () => vendorsApi.list(eventId!, filters),
    enabled: Boolean(eventId),
  })
}

export function useAiStatusQuery(eventId: string | undefined) {
  return useQuery({
    queryKey: eventId ? queryKeys.aiStatus(eventId) : ['ai-status', 'missing'],
    queryFn: () => aiPlanningApi.status(eventId!),
    enabled: Boolean(eventId),
    staleTime: 60_000,
  })
}
