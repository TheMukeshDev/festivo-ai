import { z } from 'zod'

const moneyPattern = /^\d{1,9}(\.\d{1,2})?$/

export const taskFormSchema = z.object({
  title: z
    .string()
    .trim()
    .min(1, 'Enter a task title.')
    .max(200, 'Use 200 characters or fewer.'),
  description: z.string().max(2000, 'Use 2,000 characters or fewer.'),
  status: z.enum(['pending', 'in_progress', 'completed', 'cancelled']),
  priority: z.enum(['low', 'medium', 'high', 'urgent']),
  due_at: z.string(),
  assigned_to: z.string().max(120, 'Use 120 characters or fewer.'),
  estimated_cost: z
    .string()
    .trim()
    .refine(
      (value) => value === '' || moneyPattern.test(value),
      'Use a valid amount with up to two decimal places.',
    ),
  actual_cost: z
    .string()
    .trim()
    .refine(
      (value) => value === '' || moneyPattern.test(value),
      'Use a valid amount with up to two decimal places.',
    ),
})

export type TaskFormValues = z.infer<typeof taskFormSchema>

export const emptyTaskForm: TaskFormValues = {
  title: '',
  description: '',
  status: 'pending',
  priority: 'medium',
  due_at: '',
  assigned_to: '',
  estimated_cost: '',
  actual_cost: '',
}
