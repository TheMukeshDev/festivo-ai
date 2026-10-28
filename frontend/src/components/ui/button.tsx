import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import type * as React from 'react'

import { cn } from '@/lib/utils'

export const buttonVariants = cva(
  'inline-flex shrink-0 items-center justify-center gap-2 rounded-sm text-sm font-semibold transition-colors disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        primary:
          'bg-primary text-white shadow-sm hover:bg-primary-strong focus-visible:outline-primary',
        secondary: 'bg-primary-soft text-primary-strong hover:bg-[#e3dcfa]',
        outline: 'border border-line-strong bg-surface text-ink hover:bg-canvas focus-visible:outline-primary',
        ghost: 'text-ink-soft hover:bg-canvas hover:text-ink',
        danger: 'bg-danger-strong text-white hover:bg-[#7a202a]',
        'danger-ghost': 'text-danger-strong hover:bg-danger-soft',
        link: 'text-primary underline-offset-4 hover:underline',
      },
      size: {
        sm: 'h-8 px-3 text-xs [&_svg]:size-3.5',
        default: 'h-10 px-4 [&_svg]:size-4',
        lg: 'h-11 px-5 text-[0.95rem] [&_svg]:size-4',
        icon: 'size-9 [&_svg]:size-4',
        'icon-sm': 'size-8 [&_svg]:size-3.5',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'default',
    },
  },
)

export interface ButtonProps
  extends
    React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

export function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: ButtonProps) {
  const Component = asChild ? Slot : 'button'
  return (
    <Component className={cn(buttonVariants({ variant, size }), className)} {...props} />
  )
}
