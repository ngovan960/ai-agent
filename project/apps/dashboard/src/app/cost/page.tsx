"use client"

import { motion } from "framer-motion"
import { DollarSign, Cpu } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import Breadcrumbs from "@/components/Breadcrumbs"
import { useApi } from "@/lib/hooks"
import { fetchCostBreakdown } from "@/lib/api"

export default function CostPage() {
  const { data: costs, loading, error } = useApi(fetchCostBreakdown)

  const total = Array.isArray(costs) ? costs.reduce((s: number, c: any) => s + (c.cost || c.sum_1 || 0), 0) : 0

  return (
    <div className="space-y-5 max-w-4xl mx-auto">
      <Breadcrumbs items={[{ label: "Cost" }]} />
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold text-foreground">Cost Analysis</h1>
        <p className="text-sm text-muted-foreground mt-1">LLM usage and cost tracking</p>
      </motion.div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Total Cost", value: `$${total.toFixed(4)}`, icon: DollarSign, color: "text-success-600" },
          { label: "Models", value: Array.isArray(costs) ? costs.length : 0, icon: Cpu, color: "text-primary" },
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

      {loading ? <Skeleton className="h-48" /> : error ? (
        <Card>
          <CardContent className="p-6 text-center">
            <p className="text-destructive mb-3">{error}</p>
            <Button variant="outline" size="sm" onClick={() => window.location.reload()}>Retry</Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Cost by Model</CardTitle>
          </CardHeader>
          <CardContent>
            {Array.isArray(costs) && costs.length > 0 ? (
              <div className="space-y-3">
                {costs.map((c: any, i: number) => {
                  const model = c.model || "Unknown"
                  const cost = c.cost || c.sum_1 || 0
                  const pct = total > 0 ? (cost / total) * 100 : 0
                  return (
                    <motion.div key={model} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}>
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="font-medium text-foreground">{model}</span>
                        <span className="text-muted-foreground">${Number(cost).toFixed(4)}</span>
                      </div>
                      <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                        <motion.div
                          className="h-full bg-primary rounded-full"
                          initial={{ width: 0 }}
                          animate={{ width: `${pct}%` }}
                          transition={{ duration: 0.8, delay: i * 0.1 }}
                        />
                      </div>
                    </motion.div>
                  )
                })}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground text-sm">No cost data available</div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
