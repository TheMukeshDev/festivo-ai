import { Slot } from '@radix-ui/react-slot'
import type { VariantProps } from 'class-variance-authority'
import type * as React from 'react'

import { cn } from '@/lib/utils'
import { buttonVariants } from '@/components/ui/button-variants'

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
