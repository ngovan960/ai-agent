"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import Breadcrumbs from "@/components/Breadcrumbs"

interface NodeDef {
  id: string
  x: number
  y: number
  label: string
  color: string
  count: number
}

const BASE_NODES: Omit<NodeDef, "count">[] = [
  { id: "NEW", x: 60, y: 120, label: "New", color: "#94a3b8" },
  { id: "ANALYZING", x: 200, y: 120, label: "Analyzing", color: "#6366f1" },
  { id: "PLANNING", x: 340, y: 120, label: "Planning", color: "#8b5cf6" },
  { id: "IMPLEMENTING", x: 480, y: 120, label: "Implementing", color: "#a855f7" },
  { id: "VERIFYING", x: 620, y: 120, label: "Verifying", color: "#eab308" },
  { id: "REVIEWING", x: 760, y: 120, label: "Reviewing", color: "#f97316" },
  { id: "DONE", x: 900, y: 120, label: "Done", color: "#22c55e" },
  { id: "FAILED", x: 760, y: 260, label: "Failed", color: "#ef4444" },
  { id: "ESCALATED", x: 480, y: 260, label: "Escalated", color: "#dc2626" },
  { id: "BLOCKED", x: 340, y: 260, label: "Blocked", color: "#f59e0b" },
  { id: "CANCELLED", x: 200, y: 260, label: "Cancelled", color: "#6b7280" },
]

const EDGES: { from: string; to: string }[] = [
  { from: "NEW", to: "ANALYZING" },
  { from: "ANALYZING", to: "PLANNING" },
  { from: "PLANNING", to: "IMPLEMENTING" },
  { from: "IMPLEMENTING", to: "VERIFYING" },
  { from: "VERIFYING", to: "REVIEWING" },
  { from: "REVIEWING", to: "DONE" },
  { from: "REVIEWING", to: "FAILED" },
  { from: "IMPLEMENTING", to: "ESCALATED" },
  { from: "ESCALATED", to: "FAILED" },
  { from: "ANALYZING", to: "BLOCKED" },
  { from: "PLANNING", to: "BLOCKED" },
  { from: "NEW", to: "CANCELLED" },
]

export default function WorkflowPage() {
  const [nodes, setNodes] = useState<NodeDef[]>([])
  const [loading, setLoading] = useState(true)
  const [totalTasks, setTotalTasks] = useState(0)

  useEffect(() => {
    fetchWorkflowData()
  }, [])

  const fetchWorkflowData = async () => {
    setLoading(true)
    try {
      const res = await fetch("/api/v1/dashboard/tasks-by-status")
      const data = await res.json()
      const statusMap: Record<string, number> = {}
      if (Array.isArray(data)) {
        data.forEach((s: any) => {
          statusMap[s.status || s.state] = s.count || 0
        })
      }
      const total = Object.values(statusMap).reduce((s: number, c: number) => s + c, 0)
      setTotalTasks(total)
      const enhanced = BASE_NODES.map((n) => ({
        ...n,
        count: statusMap[n.id] || 0,
      }))
      setNodes(enhanced)
    } catch {
      setNodes(BASE_NODES.map((n) => ({ ...n, count: 0 })))
    } finally {
      setLoading(false)
    }
  }

  const activeCount = nodes.filter((n) =>
    ["ANALYZING", "PLANNING", "IMPLEMENTING", "VERIFYING", "REVIEWING"].includes(n.id)
  ).reduce((s, n) => s + n.count, 0)

  return (
    <div className="space-y-5 max-w-6xl mx-auto">
      <Breadcrumbs items={[{ label: "Workflow" }]} />
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Workflow Graph</h1>
            <p className="text-sm text-muted-foreground mt-1">State machine diagram showing task workflow transitions</p>
          </div>
          {loading ? <Skeleton className="h-8 w-32" /> : (
            <div className="flex gap-2">
              <Badge variant="default">{totalTasks} total</Badge>
              <Badge variant="success">{activeCount} active</Badge>
            </div>
          )}
        </div>
      </motion.div>

      {loading ? (
        <Skeleton className="h-80" />
      ) : (
        <>
          <Card className="p-6 overflow-x-auto">
            <svg viewBox="0 0 960 320" className="w-full" style={{ minHeight: 320 }}>
              <defs>
                <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8" />
                </marker>
                <marker id="arrow-active" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#6366f1" />
                </marker>
              </defs>

              {EDGES.map((e, i) => {
                const from = nodes.find((n) => n.id === e.from)
                const to = nodes.find((n) => n.id === e.to)
                if (!from || !to) return null
                const isActive = from.count > 0
                return (
                  <motion.line key={i}
                    initial={{ pathLength: 0, opacity: 0 }}
                    animate={{ pathLength: 1, opacity: 1 }}
                    transition={{ delay: i * 0.1, duration: 0.4 }}
                    x1={from.x} y1={from.y} x2={to.x} y2={to.y}
                    stroke={isActive ? "#6366f1" : "#cbd5e1"}
                    strokeWidth={isActive ? 2.5 : 2}
                    strokeDasharray={to.id === "FAILED" || to.id === "ESCALATED" || to.id === "BLOCKED" || to.id === "CANCELLED" ? "6,4" : "none"}
                    markerEnd={isActive ? "url(#arrow-active)" : "url(#arrow)"}
                  />
                )
              })}

              {nodes.map((node, i) => (
                <motion.g key={node.id}
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: i * 0.08 + 0.3, type: "spring", stiffness: 200 }}>
                  <circle cx={node.x} cy={node.y} r={22} fill={node.color}
                    stroke={node.count > 0 ? "#fff" : "transparent"} strokeWidth={3}
                    className={node.count > 0 ? "drop-shadow-lg" : ""} />
                  <text x={node.x} y={node.y - 2} textAnchor="middle" dominantBaseline="central"
                    fill="#fff" fontSize={node.id.length > 8 ? 7 : 9} fontWeight="bold">
                    {node.id === "IMPLEMENTING" ? "IMPL" : node.id === "ANALYZING" ? "ANLZ" : node.id.substring(0, 4)}
                  </text>
                  {node.count > 0 && (
                    <text x={node.x} y={node.y + 10} textAnchor="middle" dominantBaseline="central"
                      fill="#fff" fontSize={11} fontWeight="bold">
                      {node.count}
                    </text>
                  )}
                  <text x={node.x} y={node.y + 40} textAnchor="middle"
                    fill={node.count > 0 ? "#e2e8f0" : "#64748b"} fontSize={10} fontWeight="medium">
                    {node.label}
                  </text>
                </motion.g>
              ))}
            </svg>
          </Card>

          <Card>
            <CardContent className="p-5">
              <h2 className="text-sm font-semibold text-foreground mb-3">Status Legend</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {nodes.map((node) => (
                  <div key={node.id} className="flex items-center gap-2 text-sm text-muted-foreground">
                    <div className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: node.color }} />
                    <span className="flex-1">{node.label}</span>
                    {node.count > 0 && <Badge variant="outline" className="text-xs">{node.count}</Badge>}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
