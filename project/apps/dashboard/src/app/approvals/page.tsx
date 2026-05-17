"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Shield, CheckCircle, XCircle, RefreshCw } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import Breadcrumbs from "@/components/Breadcrumbs"
import { useToast } from "@/lib/toast"

interface ApprovalRequest {
  approval_id: string
  deployment_id: string
  task_id: string
  reason: string
  risk_level: string
  status: string
  created_at: string
  approver?: string
  rejection_reason?: string
}

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([])
  const [history, setHistory] = useState<ApprovalRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [rejectTarget, setRejectTarget] = useState<string | null>(null)
  const [rejectReason, setRejectReason] = useState("")
  const { toast } = useToast()

  useEffect(() => {
    fetchApprovals()
  }, [])

  const fetchApprovals = async () => {
    setLoading(true)
    setError(null)
    try {
      const [pendingRes, historyRes] = await Promise.all([
        fetch("/api/v1/deploy/pending-approvals"),
        fetch("/api/v1/deploy/approval-history"),
      ])
      setApprovals(await pendingRes.json())
      setHistory(await historyRes.json())
    } catch {
      setError("Failed to load approvals.")
    } finally {
      setLoading(false)
    }
  }

  const handleApprove = async (approvalId: string) => {
    try {
      const res = await fetch("/api/v1/deploy/production/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approval_id: approvalId, approver: "dashboard-user" }),
      })
      if (res.ok) {
        toast("success", "Deployment approved")
        fetchApprovals()
      } else {
        toast("destructive", "Failed to approve")
      }
    } catch {
      toast("destructive", "Network error")
    }
  }

  const handleReject = async (approvalId: string) => {
    setRejectTarget(approvalId)
    setRejectReason("")
  }

  const confirmReject = async () => {
    if (!rejectTarget) return
    if (!rejectReason.trim()) {
      toast("destructive", "Please enter a reason")
      return
    }
    try {
      const res = await fetch("/api/v1/deploy/production/reject", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approval_id: rejectTarget, reason: rejectReason }),
      })
      if (res.ok) {
        toast("success", "Deployment rejected")
        setRejectTarget(null)
        setRejectReason("")
        fetchApprovals()
      } else {
        toast("destructive", "Failed to reject")
      }
    } catch {
      toast("destructive", "Network error")
    }
  }

  const getBadgeVariant = (status: string): "success" | "destructive" | "warning" | "neutral" => {
    if (status === "approved") return "success"
    if (status === "rejected") return "destructive"
    if (status === "timed_out") return "neutral"
    return "warning"
  }

  const shortId = (id: string | undefined) => id ? id.slice(0, 8) : "???"

  if (loading) {
    return (
      <div className="space-y-5 max-w-4xl mx-auto">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-2 gap-3">
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
        <Skeleton className="h-64" />
      </div>
    )
  }

  return (
    <div className="space-y-5 max-w-4xl mx-auto">
      <Breadcrumbs items={[{ label: "Approvals" }]} />
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Approvals</h1>
          <p className="text-sm text-muted-foreground mt-1">Production deployment approvals and rollback history</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchApprovals}>
          <RefreshCw className="w-4 h-4" />
          Refresh
        </Button>
      </motion.div>

      <div className="grid grid-cols-2 gap-3">
        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => document.getElementById("pending-section")?.scrollIntoView({ behavior: "smooth" })}>
          <CardContent className="p-4"><p className="text-xs text-muted-foreground">Pending</p><p className="text-lg font-bold text-warning-500">{approvals.length}</p></CardContent>
        </Card>
        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => document.getElementById("history-section")?.scrollIntoView({ behavior: "smooth" })}>
          <CardContent className="p-4"><p className="text-xs text-muted-foreground">History</p><p className="text-lg font-bold text-foreground">{history.length}</p></CardContent>
        </Card>
      </div>

      {error && (
        <div className="text-center py-4 text-destructive">{error}</div>
      )}

      {approvals.length > 0 ? (
        <div id="pending-section" className="space-y-3">
          <h2 className="text-lg font-semibold text-foreground">Pending Approvals</h2>
          {approvals.map((a, i) => (
            <motion.div key={a.approval_id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1 min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <Shield className="w-4 h-4 text-warning-500" />
                        <p className="font-medium text-foreground">Deployment {shortId(a.deployment_id)}</p>
                        <Badge variant="warning">{a.risk_level}</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">{a.reason}</p>
                      <p className="text-xs text-muted-foreground">
                        Created: {new Date(a.created_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="flex gap-2 shrink-0">
                      <Button size="sm" variant="default" onClick={() => handleApprove(a.approval_id)}>
                        <CheckCircle className="w-4 h-4" />
                        Approve
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => handleReject(a.approval_id)}>
                        <XCircle className="w-4 h-4" />
                        Reject
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 text-muted-foreground text-sm">
          No pending approvals.
        </div>
      )}

      {history.length > 0 && (
        <div id="history-section" className="space-y-3">
          <h2 className="text-lg font-semibold text-foreground mt-6">Approval History</h2>
          {history.map((h, i) => (
            <motion.div key={h.approval_id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}>
              <Card>
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="space-y-1 min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      {h.status === "approved" ? (
                        <CheckCircle className="w-4 h-4 text-success-500" />
                      ) : (
                        <XCircle className="w-4 h-4 text-destructive" />
                      )}
                      <p className="font-medium text-foreground">
                        {h.status.charAt(0).toUpperCase() + h.status.slice(1)}
                      </p>
                      {h.approver && <span className="text-xs text-muted-foreground">by {h.approver}</span>}
                    </div>
                    <p className="text-xs text-muted-foreground">{h.reason}</p>
                  </div>
                  <Badge variant={getBadgeVariant(h.status)}>{h.status}</Badge>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}

      {rejectTarget && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setRejectTarget(null)}>
          <div className="bg-card border rounded-lg p-6 w-full max-w-md shadow-xl" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-foreground mb-3">Reject Deployment</h3>
            <p className="text-sm text-muted-foreground mb-4">Enter a reason for rejecting this deployment request.</p>
            <textarea
              className="w-full border rounded-md p-2 text-sm bg-background text-foreground min-h-[80px]"
              placeholder="Reason for rejection..."
              value={rejectReason}
              onChange={e => setRejectReason(e.target.value)}
              autoFocus
            />
            <div className="flex justify-end gap-2 mt-4">
              <Button variant="outline" size="sm" onClick={() => setRejectTarget(null)}>Cancel</Button>
              <Button variant="destructive" size="sm" onClick={confirmReject}>Reject</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
