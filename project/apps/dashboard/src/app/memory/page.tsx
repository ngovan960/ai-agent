"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { BookOpen, Lightbulb, ScrollText } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import Breadcrumbs from "@/components/Breadcrumbs"
import { useToast } from "@/lib/toast"
import api from "@/lib/api"

interface MemoryItem {
  id: string
  content: string
  type: string
  source: string
  created_at: string
}

export default function MemoryPage() {
  const [items, setItems] = useState<MemoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<string>("all")
  const { toast } = useToast()

  useEffect(() => {
    fetchMemory()
  }, [])

  const fetchMemory = async () => {
    setLoading(true)
    setError(null)
    try {
      const [instrRes, decRes] = await Promise.all([
        api.get("/instructions"),
        api.get("/decisions"),
      ])
      const instructions = (instrRes.data?.items || []).map((i: any) => ({
        id: i.id,
        content: i.content,
        type: "instruction",
        source: i.source || "System",
        created_at: i.created_at,
      }))
      const decisions = (decRes.data?.items || []).map((d: any) => ({
        id: d.id,
        content: d.content,
        type: "decision",
        source: d.source || "System",
        created_at: d.created_at,
      }))
      setItems([...instructions, ...decisions].sort((a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      ))
    } catch {
      setError("Failed to load memory. Please try again.")
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  const filtered = filter === "all" ? items : items.filter((i) => i.type === filter)

  const counts = {
    instruction: items.filter((i) => i.type === "instruction").length,
    decision: items.filter((i) => i.type === "decision").length,
  }

  return (
    <div className="space-y-5 max-w-4xl mx-auto">
      <Breadcrumbs items={[{ label: "Memory" }]} />
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold text-foreground">Memory</h1>
        <p className="text-sm text-muted-foreground mt-1">Stored instructions, decisions, and patterns</p>
      </motion.div>

      <div className="grid grid-cols-3 gap-3">
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Total</p><p className="text-lg font-bold text-foreground">{items.length}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Instructions</p><p className="text-lg font-bold text-primary">{counts.instruction}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">Decisions</p><p className="text-lg font-bold text-warning-500">{counts.decision}</p></CardContent></Card>
      </div>

      <div className="flex gap-2 flex-wrap">
        {["all", "instruction", "decision"].map((s) => (
          <Badge key={s} variant={filter === s ? "default" : "outline"}
            className="cursor-pointer" onClick={() => setFilter(s)}>
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </Badge>
        ))}
      </div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20" />)}
        </div>
      ) : error ? (
        <div className="text-center py-12">
          <p className="text-destructive mb-3">{error}</p>
          <Badge className="cursor-pointer" onClick={fetchMemory}>Retry</Badge>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((item, i) => (
            <motion.div key={item.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}>
              <Card className="card-hover">
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center shrink-0 mt-0.5">
                      {item.type === "instruction" ? <BookOpen className="w-4 h-4 text-primary" /> :
                       <ScrollText className="w-4 h-4 text-warning-500" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant={item.type === "instruction" ? "default" : "warning"}>{item.type}</Badge>
                        <span className="text-xs text-muted-foreground">{new Date(item.created_at).toLocaleDateString()}</span>
                      </div>
                      <p className="text-sm text-foreground">{item.content}</p>
                      <p className="text-xs text-muted-foreground mt-1">Source: {item.source}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
          {filtered.length === 0 && (
            <div className="text-center py-12 text-muted-foreground text-sm">
              {items.length === 0 ? "No memory items yet. Instructions and decisions will appear here as the AI works." : "No items match your filter."}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
