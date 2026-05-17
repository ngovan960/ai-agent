"use client"

import { motion } from "framer-motion"
import { Bot, Activity, Clock, Zap } from "lucide-react"
import { useState, useEffect } from "react"
import Breadcrumbs from "@/components/Breadcrumbs"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { useToast } from "@/lib/toast"

interface AgentInfo {
  name: string
  role: string
  status: string
  current_task: string | null
  total_calls: number
  success_rate: number
  last_active: string | null
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { toast } = useToast()

  useEffect(() => {
    fetchAgents()
  }, [])

  const fetchAgents = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch("/api/v1/agents/")
      if (!res.ok) throw new Error("Failed to fetch agents")
      const data = await res.json()
      setAgents(Array.isArray(data) ? data : [])
    } catch {
      setError("Failed to load agents. Please try again.")
      setAgents([])
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-5 max-w-5xl mx-auto">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20" />)}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
      </div>
    )
  }

  const totalCalls = agents.reduce((s, a) => s + a.total_calls, 0)
  const activeCount = agents.filter((a) => a.status === "working" || a.status === "busy").length

  return (
    <div className="space-y-5 max-w-5xl mx-auto">
      <Breadcrumbs items={[{ label: "Agents" }]} />
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Agents</h1>
            <p className="text-sm text-muted-foreground mt-1">Monitor all AI agents in the system</p>
          </div>
          {error && (
            <Badge className="cursor-pointer" onClick={fetchAgents}>Retry</Badge>
          )}
        </div>
      </motion.div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Total Agents", value: agents.length, icon: Bot },
          { label: "Active Now", value: activeCount, icon: Activity, color: "text-success-600" },
          { label: "Total Calls", value: totalCalls, icon: Zap, color: "text-primary" },
          { label: "Idle", value: agents.length - activeCount, icon: Clock, color: "text-muted-foreground" },
        ].map((s, i) => {
          const Icon = s.icon
          return (
            <Card key={i}>
              <CardContent className="p-4 flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-muted flex items-center justify-center">
                  <Icon className={`w-4 h-4 ${s.color || "text-muted-foreground"}`} />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{s.label}</p>
                  <p className="text-lg font-bold text-foreground">{s.value}</p>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {error && (
        <div className="text-center py-4">
          <p className="text-destructive mb-3">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {agents.map((agent, i) => (
          <motion.div
            key={agent.name}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
          >
            <Card className="card-hover">
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center transition-colors ${
                      agent.status === "working" || agent.status === "busy" ? "bg-primary/10" : "bg-muted"
                    }`}>
                      <Bot className={`w-5 h-5 ${agent.status === "working" || agent.status === "busy" ? "text-primary" : "text-muted-foreground"}`} />
                    </div>
                    <div>
                      <p className="font-medium text-foreground">{agent.name}</p>
                      <p className="text-xs text-muted-foreground">{agent.role}</p>
                    </div>
                  </div>
                  <Badge variant={agent.status === "working" || agent.status === "busy" ? "success" : "neutral"}>
                    <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${agent.status === "working" || agent.status === "busy" ? "bg-success-500 animate-pulse" : "bg-muted-foreground"}`} />
                    {agent.status}
                  </Badge>
                </div>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{agent.total_calls} calls processed</span>
                  {agent.success_rate > 0 && <span>{agent.success_rate.toFixed(1)}% success</span>}
                </div>
                {agent.current_task && (
                  <p className="text-xs text-muted-foreground mt-2 truncate">
                    Working on: {agent.current_task}
                  </p>
                )}
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {agents.length === 0 && !error && (
        <div className="text-center py-12 text-muted-foreground text-sm">
          No agents registered. Agents will appear here when the system starts.
        </div>
      )}
    </div>
  )
}
