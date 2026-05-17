"use client"

import { Skeleton } from "@/components/ui/skeleton"
import { LayoutDashboard, CheckSquare2, DollarSign, BookOpen, FileText, Briefcase } from "lucide-react"
import { motion } from "framer-motion"
import Breadcrumbs from "@/components/Breadcrumbs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useApi } from "@/lib/hooks"
import { fetchSummary as fetchDashboardSummary } from "@/lib/api"
import Link from "next/link"
import type { DashboardSummary } from "@/types"

export default function HomePage() {
  const { data: summary, loading, error } = useApi(fetchDashboardSummary)

  if (loading) return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <Skeleton className="h-8 w-48" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-28" />)}
      </div>
    </div>
  )

  if (error) return (
    <div className="max-w-7xl mx-auto text-center py-20">
      <p className="text-destructive">{error}</p>
    </div>
  )

  if (!summary) return null

  const cards = [
    { key: "projects", label: "Projects", value: summary.projects, icon: Briefcase, href: "/projects" },
    { key: "tasks", label: "Total Tasks", value: summary.tasks, icon: CheckSquare2, href: "/tasks" },
    { key: "active_tasks", label: "Active Tasks", value: summary.active_tasks, icon: LayoutDashboard, href: "/tasks" },
    { key: "instructions", label: "Instructions", value: summary.instructions, icon: BookOpen, href: "/memory" },
    { key: "decisions", label: "Decisions", value: summary.decisions, icon: FileText, href: "/memory" },
    { key: "total_cost", label: "Total Cost", value: `$${summary.total_cost?.toFixed(4) || "0.00"}`, icon: DollarSign, href: "/cost" },
  ]

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <Breadcrumbs items={[{ label: "Dashboard" }]} />
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center justify-between mb-1">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
            <p className="text-sm text-muted-foreground mt-1">Overview of your SDLC system</p>
          </div>
          <Button asChild variant="outline" size="sm">
            <Link href="/tasks">View Tasks</Link>
          </Button>
        </div>
      </motion.div>

      <motion.div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" initial="hidden" animate="visible" variants={{ visible: { transition: { staggerChildren: 0.05 } } }}>
        {cards.map((card, i) => {
          const Icon = card.icon
          return (
            <motion.div key={card.key} variants={{ hidden: { opacity: 0, y: 12 }, visible: { opacity: 1, y: 0 } }}>
              <Link href={card.href}>
                <Card className="card-hover cursor-pointer h-full">
                  <CardContent className="p-5">
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <p className="text-sm text-muted-foreground">{card.label}</p>
                        <p className="text-2xl font-bold text-foreground">{card.value}</p>
                      </div>
                      <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                        <Icon className="w-5 h-5 text-primary" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            </motion.div>
          )
        })}
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-3">
            <Button asChild variant="default" size="sm"><Link href="/tasks">Browse Tasks</Link></Button>
            <Button asChild variant="outline" size="sm"><Link href="/audit">Audit Log</Link></Button>
            <Button asChild variant="outline" size="sm"><Link href="/cost">Cost Report</Link></Button>
            <Button asChild variant="outline" size="sm"><Link href="/agents">Agent Status</Link></Button>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}
