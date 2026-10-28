import type { VariantProps } from 'class-variance-authority'
import { Children, cloneElement, type ReactElement, type ReactNode } from 'react'

import { cn } from '@/lib/utils'
import { buttonVariants } from '@/components/ui/button-variants'

export interface ButtonProps
  extends
    React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

export function Button({
  className: buttonClassName,
  variant,
  size,
  asChild = false,
  children,
  ...props
}: ButtonProps) {
  const className = cn(buttonVariants({ variant, size }), buttonClassName)
  if (asChild) {
    const child = Children.only(children) as ReactElement<{ className?: string }>
    return cloneElement(child, {
      ...props,
      className: cn(className, child.props.className),
    })
  }

  const Component = 'button'
  return (
    <Component className={className} {...props}>
      {children as ReactNode}
    </Component>
  )
}
