import { z } from 'zod'

const moneyPattern = /^\d{1,9}(\.\d{1,2})?$/

export const expenseFormSchema = z.object({
  category: z
    .string()
    .trim()
    .min(1, 'Choose or enter a category.')
    .max(80, 'Use 80 characters or fewer.'),
  name: z
    .string()
    .trim()
    .min(1, 'Enter an expense name.')
    .max(120, 'Use 120 characters or fewer.'),
  amount: z
    .string()
    .trim()
    .min(1, 'Enter an amount.')
    .regex(moneyPattern, 'Use a valid amount with up to two decimal places.')
    .refine((value) => Number(value) > 0, 'Amount must be greater than zero.'),
  amount_status: z.enum(['estimated', 'quoted', 'confirmed']),
  notes: z.string().max(500, 'Use 500 characters or fewer.'),
})

export type ExpenseFormValues = z.infer<typeof expenseFormSchema>

export const budgetCreateSchema = z.object({
  total_limit: z
    .string()
    .trim()
    .min(1, 'Enter the budget limit.')
    .regex(moneyPattern, 'Use a valid amount with up to two decimal places.')
    .refine((value) => Number(value) > 0, 'Budget must be greater than zero.'),
  reserve_type: z.enum(['percentage', 'fixed_amount']),
  reserve_value: z
    .string()
    .trim()
    .min(1, 'Enter a reserve value.')
    .regex(moneyPattern, 'Use a number with up to two decimal places.'),
})

export type BudgetCreateValues = z.infer<typeof budgetCreateSchema>

export const budgetUpdateSchema = budgetCreateSchema

export type BudgetUpdateValues = z.infer<typeof budgetUpdateSchema>
