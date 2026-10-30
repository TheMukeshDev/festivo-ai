import axe from 'axe-core'
import { expect } from 'vitest'

export async function expectNoA11yViolations(container: HTMLElement) {
  const results = await axe.run(container, {
    rules: {
      'color-contrast': { enabled: false },
    },
  })

  const violations = results.violations.map((violation) => ({
    id: violation.id,
    impact: violation.impact,
    help: violation.help,
    targets: violation.nodes.map((node) => node.target.join(' ')),
  }))

  expect(violations).toEqual([])
}
