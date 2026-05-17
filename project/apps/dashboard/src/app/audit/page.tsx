"use client"

import { motion } from "framer-motion"
import { FileText, Download, Search, ChevronLeft, ChevronRight } from "lucide-react"
import { useState } from "react"
import Breadcrumbs from "@/components/Breadcrumbs"
import { useToast } from "@/lib/toast"
import { useApi } from "@/lib/hooks"
import { fetchRecentActivity } from "@/lib/api"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"

const PAGE_SIZE = 10

export default function AuditPage() {
  const [search, setSearch] = useState("")
  const [filter, setFilter] = useState<string>("all")
  const [page, setPage] = useState(1)
  const { toast } = useToast()
  const activity = useApi(() => fetchRecentActivity(50))

  const filtered = (activity.data || []).filter((log: any) => {
    if (filter !== "all" && log.result !== filter) return false
    if (search && !log.action.toLowerCase().includes(search.toLowerCase()) && !log.actor.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const paged = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const exportCSV = () => {
    const header = "Time,Action,Actor,Result,Message\n"
    const rows = filtered.map((log: any) =>
      `"${new Date(log.created_at).toLocaleString()}","${log.action}","${log.actor}","${log.result}","${(log.message || "").replace(/"/g, '""')}"`
    ).join("\n")
    const blob = new Blob([header + rows], { type: "text/csv" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `audit-logs-${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
    toast("success", `Exported ${filtered.length} log entries`)
  }

  const resultBadge = (result: string): "success" | "destructive" | "neutral" => {
    if (result === "SUCCESS" || result === "APPROVED") return "success"
    if (result === "FAILURE" || result === "REJECTED") return "destructive"
    return "neutral"
  }

  return (
    <div className="space-y-5 max-w-6xl mx-auto">
      <Breadcrumbs items={[{ label: "Audit Logs" }]} />

      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Audit Logs</h1>
          <p className="text-sm text-muted-foreground mt-1">Complete audit trail of all system actions</p>
        </div>
        <Button variant="outline" size="sm" onClick={exportCSV}>
          <Download className="w-4 h-4" />
          Export CSV
        </Button>
      </motion.div>

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input type="text" placeholder="Search by action or actor..." value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }} className="pl-9" />
        </div>
        <div className="flex gap-2 flex-wrap">
          {["all", "SUCCESS", "FAILURE", "APPROVED", "REJECTED"].map((s) => (
            <Button key={s} variant={filter === s ? "default" : "outline"} size="sm"
              onClick={() => { setFilter(s); setPage(1) }}>
              {s === "all" ? "All" : s.charAt(0) + s.slice(1).toLowerCase()}
            </Button>
          ))}
        </div>
      </div>

      {activity.loading ? (
        <Skeleton className="h-64" />
      ) : activity.error ? (
        <Card>
          <CardContent className="p-6 text-center">
            <p className="text-destructive mb-3">{activity.error}</p>
            <Button variant="outline" size="sm" onClick={activity.refetch}>Retry</Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-36">Time</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead className="w-24">Result</TableHead>
                  <TableHead className="w-48">Message</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paged.map((log: any, i: number) => (
                  <motion.tr key={log.id || i}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.03 }}
                    className="border-b transition-colors hover:bg-muted/50">
                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                      {new Date(log.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="font-medium">{log.action}</TableCell>
                    <TableCell className="text-muted-foreground">{log.actor}</TableCell>
                    <TableCell>
                      <Badge variant={resultBadge(log.result)}>{log.result}</Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground max-w-[200px] truncate">{log.message}</TableCell>
                  </motion.tr>
                ))}
              </TableBody>
            </Table>

            {filtered.length === 0 && (
              <div className="text-center py-8 text-muted-foreground text-sm">No logs match your filters.</div>
            )}

            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t">
                <span className="text-xs text-muted-foreground">{filtered.length} total entries</span>
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="icon" onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1}>
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  <span className="text-xs text-muted-foreground">{page}/{totalPages}</span>
                  <Button variant="ghost" size="icon" onClick={() => setPage(Math.min(totalPages, page + 1))} disabled={page === totalPages}>
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
