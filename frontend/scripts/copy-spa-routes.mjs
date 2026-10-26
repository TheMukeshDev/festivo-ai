import { cp, mkdir } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendDirectory = path.dirname(fileURLToPath(import.meta.url))
const distDirectory = path.resolve(frontendDirectory, '..', 'dist')
const indexFile = path.join(distDirectory, 'index.html')

for (const route of ['auth/callback', 'reset-password']) {
  const routeDirectory = path.join(distDirectory, route)
  await mkdir(routeDirectory, { recursive: true })
  await cp(indexFile, path.join(routeDirectory, 'index.html'))
}
