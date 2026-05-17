"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { CheckSquare2, Clock, AlertTriangle, User, Plus } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import Breadcrumbs from "@/components/Breadcrumbs"
import { Skeleton } from "@/components/ui/skeleton"
import { useToast } from "@/lib/toast"
import api from "@/lib/api"

import type { TaskItem, ProjectItem } from "@/types"

const STATUS_COLORS: Record<string, "success" | "warning" | "destructive" | "secondary" | "neutral"> = {
  DONE: "success",
  NEW: "neutral",
  ANALYZING: "secondary",
  PLANNING: "secondary",
  IMPLEMENTING: "warning",
  VERIFYING: "secondary",
  REVIEWING: "warning",
  BLOCKED: "destructive",
  FAILED: "destructive",
  ESCALATED: "destructive",
  CANCELLED: "neutral",
}

export default function TasksPage() {
  const [search, setSearch] = useState("")
  const [tasks, setTasks] = useState<TaskItem[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const { toast } = useToast()

  // Form state
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [priority, setPriority] = useState("MEDIUM")
  const [owner, setOwner] = useState("")
  const [projectId, setProjectId] = useState("")
  const [projects, setProjects] = useState<ProjectItem[]>([])

  useEffect(() => {
    fetchTasks()
    fetchProjects()
  }, [])

  const fetchProjects = async () => {
    try {
      const { data } = await api.get("/projects")
      const items = data?.items || []
      setProjects(items)
      if (items.length === 1) setProjectId(items[0].id)
    } catch {
      setProjects([])
    }
  }

  const fetchTasks = async () => {
    try {
      const { data } = await api.get("/tasks")
      const items = Array.isArray(data) ? data : (data?.items || [])
      setTasks(items)
    } catch {
      setTasks([])
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async () => {
    if (!title.trim()) {
      toast("destructive", "Task title is required")
      return
    }
    if (!projectId) {
      toast("destructive", "Please select a project")
      return
    }
    setSubmitting(true)
    try {
      await api.post("/tasks", {
        title: title.trim(),
        description: description.trim() || undefined,
        priority,
        owner: owner.trim() || undefined,
        project_id: projectId,
      })
      toast("success", `Task "${title}" created`)
      setTitle("")
      setDescription("")
      setPriority("MEDIUM")
      setOwner("")
      setOpen(false)
      fetchTasks()
    } catch (e: any) {
      toast("destructive", e.response?.data?.detail || "Failed to create task")
    } finally {
      setSubmitting(false)
    }
  }

  const filtered = tasks.filter((t) =>
    t.title.toLowerCase().includes(search.toLowerCase())
  )

  const stats = {
    total: tasks.length,
    done: tasks.filter((t) => t.status === "DONE").length,
    active: tasks.filter((t) => !["DONE", "CANCELLED", "FAILED"].includes(t.status)).length,
    blocked: tasks.filter((t) => t.status === "BLOCKED").length,
  }

  return (
    <div className="space-y-5 max-w-5xl mx-auto">
      <Breadcrumbs items={[{ label: "Tasks" }]} />
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Tasks</h1>
          <p className="text-sm text-muted-foreground mt-1">Track and manage all system tasks</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button size="sm">
              <Plus className="w-4 h-4" />
              Add Task
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Task</DialogTitle>
              <DialogDescription>
                Describe the task. The AI will analyze, plan, and execute it automatically.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div>
                <label className="text-sm font-medium text-foreground mb-1.5 block">Project *</label>
                <Select value={projectId} onValueChange={setProjectId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a project" />
                  </SelectTrigger>
                  <SelectContent>
                    {projects.map((p) => (
                      <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium text-foreground mb-1.5 block">Title *</label>
                <Input placeholder="e.g., Implement user authentication" value={title}
                  onChange={(e) => setTitle(e.target.value)} />
              </div>
              <div>
                <label className="text-sm font-medium text-foreground mb-1.5 block">Description</label>
                <Textarea placeholder="Describe what needs to be done..." value={description}
                  onChange={(e) => setDescription(e.target.value)} rows={3} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-sm font-medium text-foreground mb-1.5 block">Priority</label>
                  <Select value={priority} onValueChange={setPriority}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="LOW">Low</SelectItem>
                      <SelectItem value="MEDIUM">Medium</SelectItem>
                      <SelectItem value="HIGH">High</SelectItem>
                      <SelectItem value="CRITICAL">Critical</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-sm font-medium text-foreground mb-1.5 block">Owner</label>
                  <Input placeholder="e.g., Specialist" value={owner}
                    onChange={(e) => setOwner(e.target.value)} />
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button onClick={handleCreate} disabled={submitting || !title.trim()}>
                {submitting ? "Creating..." : "Create Task"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </motion.div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Total", value: stats.total, icon: CheckSquare2 },
          { label: "Done", value: stats.done, icon: CheckSquare2, color: "text-success-600" },
          { label: "Active", value: stats.active, icon: Clock, color: "text-primary" },
          { label: "Blocked", value: stats.blocked, icon: AlertTriangle, color: "text-destructive" },
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

      <div className="flex gap-3">
        <Input placeholder="Search tasks..." value={search}
          onChange={(e) => setSearch(e.target.value)} className="max-w-sm" />
      </div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20" />)}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((task, i) => (
            <motion.div key={task.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}>
              <Card className="card-hover">
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="space-y-1 min-w-0">
                    <p className="font-medium text-foreground truncate">{task.title}</p>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      {task.owner && (
                        <span className="flex items-center gap-1"><User className="w-3 h-3" /> {task.owner}</span>
                      )}
                      <span className={task.priority === "CRITICAL" || task.priority === "HIGH" ? "text-destructive font-medium" : ""}>
                        {task.priority}
                      </span>
                    </div>
                  </div>
                  <Badge variant={STATUS_COLORS[task.status] || "neutral"}>{task.status}</Badge>
                </CardContent>
              </Card>
            </motion.div>
          ))}
          {filtered.length === 0 && (
            <div className="text-center py-12 text-muted-foreground text-sm">
              {tasks.length === 0 ? "No tasks yet. Click 'Add Task' to create one." : "No tasks match your search."}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
