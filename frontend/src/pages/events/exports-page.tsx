import { useState } from 'react'
import { Download, FileSpreadsheet, FileText } from 'lucide-react'
import { useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { exportsApi } from '@/lib/api/queries'
import { saveDownloadedFile } from '@/lib/api/client'
import { useEventQuery } from '@/features/events/queries'

export function ExportsPage() {
  const { eventId } = useParams()
  const eventQuery = useEventQuery(eventId)
  const [downloading, setDownloading] = useState<'pdf' | 'csv' | null>(null)

  if (!eventId) return null
  const download = async (kind: 'pdf' | 'csv') => {
    if (downloading) return
    setDownloading(kind)
    try {
      const file = await (kind === 'pdf'
        ? exportsApi.pdf(eventId)
        : exportsApi.csv(eventId))
      saveDownloadedFile(file)
      toast.success(`${kind.toUpperCase()} report downloaded.`)
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : 'The report could not be downloaded.',
      )
    } finally {
      setDownloading(null)
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <p className="eyebrow">Portable planning records</p>
        <h2 className="font-display text-2xl text-ink">Exports</h2>
        <p className="mt-1 max-w-2xl text-sm leading-6 text-muted">
          Download the latest authoritative plan for {eventQuery.data?.name ?? 'this event'}
          .
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <FileText className="size-6 text-primary" aria-hidden="true" />
            <CardTitle>PDF event report</CardTitle>
            <p className="text-sm text-muted">
              A readable report with the event brief, budget, tasks, and vendors.
            </p>
          </CardHeader>
          <CardContent>
            <Button onClick={() => download('pdf')} disabled={Boolean(downloading)}>
              <Download aria-hidden="true" />
              {downloading === 'pdf' ? 'Preparing…' : 'Download PDF'}
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <FileSpreadsheet className="size-6 text-primary" aria-hidden="true" />
            <CardTitle>CSV planning data</CardTitle>
            <p className="text-sm text-muted">
              A spreadsheet-friendly export of the event planning sections.
            </p>
          </CardHeader>
          <CardContent>
            <Button onClick={() => download('csv')} disabled={Boolean(downloading)}>
              <Download aria-hidden="true" />
              {downloading === 'csv' ? 'Preparing…' : 'Download CSV'}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
