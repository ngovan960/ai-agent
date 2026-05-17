"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import AlertBanner from "@/components/AlertBanner"
import { Bell, Trash2, RefreshCw } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import Breadcrumbs from "@/components/Breadcrumbs"

interface AlertItem {
  id: string
  severity: "error" | "warning" | "info"
  message: string
  action: string
  actor: string
  result: string
  created_at: string
}

const SEVERITY_MAP: Record<string, "error" | "warning" | "info"> = {
  FAILURE: "error",
  REJECTED: "error",
  ERROR: "error",
  TIMEOUT: "error",
  WARNING: "warning",
  ESCALATED: "warning",
  BLOCKED: "warning",
  SUCCESS: "info",
  APPROVED: "info",
  CREATED: "info",
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<string>("all")

  useEffect(() => {
    fetchAlerts()
  }, [])

  const fetchAlerts = async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await fetch("/api/v1/dashboard/recent-activity?limit=100").then((r) => r.json())
      const logs = Array.isArray(data) ? data : []
      const alertLogs = logs.filter((log: any) => {
        const result = (log.result || "").toUpperCase()
        return result === "FAILURE" || result === "REJECTED" || result === "ERROR" ||
               result === "ESCALATED" || result === "BLOCKED" || result === "WARNING" ||
               result === "TIMEOUT"
      })
      const mapped = alertLogs.map((log: any) => ({
        id: log.id || `${log.action}-${log.created_at}`,
        severity: SEVERITY_MAP[log.result?.toUpperCase()] || "warning",
        message: log.message || `${log.action} by ${log.actor}`,
        action: log.action,
        actor: log.actor,
        result: log.result,
        created_at: log.created_at,
      }))
      setAlerts(mapped)
    } catch {
      setError("Failed to load alerts. Please try again.")
      setAlerts([])
    } finally {
      setLoading(false)
    }
  }

  const dismissAlert = (id: string) => setAlerts((prev) => prev.filter((a) => a.id !== id))
  const dismissAll = () => setAlerts([])

  const filtered = filter === "all" ? alerts : alerts.filter((a) => a.severity === filter)
  const counts = {
    error: alerts.filter((a) => a.severity === "error").length,
    warning: alerts.filter((a) => a.severity === "warning").length,
    info: alerts.filter((a) => a.severity === "info").length,
  }

  if (loading) {
    return (
      <div className="space-y-5 max-w-4xl mx-auto">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-3 gap-3">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16" />)}
        </div>
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-14" />)}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-5 max-w-4xl mx-auto">
      <Breadcrumbs items={[{ label: "Alerts" }]} />
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Alerts & Failures</h1>
          <p className="text-sm text-muted-foreground mt-1">Real-time alerts, failed tasks, and system bottlenecks</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={fetchAlerts}>
            <RefreshCw className="w-4 h-4" />
            Refresh
          </Button>
          {alerts.length > 0 && (
            <Button variant="outline" size="sm" onClick={dismissAll}>
              <Trash2 className="w-4 h-4" />
              Dismiss All
            </Button>
          )}
        </div>
      </motion.div>

      <div className="grid grid-cols-3 gap-3">
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Total</p><p className="text-lg font-bold text-foreground">{alerts.length}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Errors</p><p className="text-lg font-bold text-destructive">{counts.error}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Warnings</p><p className="text-lg font-bold text-warning-500">{counts.warning}</p></CardContent></Card>
      </div>

      {error && (
        <div className="text-center py-4">
          <p className="text-destructive mb-3">{error}</p>
          <Badge className="cursor-pointer" onClick={fetchAlerts}>Retry</Badge>
        </div>
      )}

      <div className="flex gap-2 flex-wrap">
        {["all", "error", "warning", "info"].map((s) => (
          <Button key={s} variant={filter === s ? "default" : "outline"} size="sm" onClick={() => setFilter(s)}>
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </Button>
        ))}
      </div>

      <AnimatePresence mode="popLayout">
        <div className="space-y-2">
          {filtered.map((a) => (
            <motion.div key={a.id} layout initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, height: 0 }}>
              <AlertBanner severity={a.severity} message={a.message} onDismiss={() => dismissAlert(a.id)} />
            </motion.div>
          ))}
        </div>
      </AnimatePresence>

      {filtered.length === 0 && (
        <div className="text-center py-12 text-muted-foreground text-sm">
          No {filter === "all" ? "" : filter} alerts. All systems nominal.
        </div>
      )}
    </div>
  )
}
