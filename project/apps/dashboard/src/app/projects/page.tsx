"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Briefcase, Plus, Trash2, Edit2, Search } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import Breadcrumbs from "@/components/Breadcrumbs"
import { Skeleton } from "@/components/ui/skeleton"
import { useToast } from "@/lib/toast"
import api from "@/lib/api"

interface ProjectItem {
  id: string
  name: string
  description: string | null
  status: string
  created_at: string
  tech_stack: string[]
}

const STATUS_COLORS: Record<string, "success" | "warning" | "destructive" | "neutral" | "secondary"> = {
  ACTIVE: "success",
  ARCHIVED: "neutral",
  COMPLETED: "secondary",
  ON_HOLD: "warning",
  FAILED: "destructive",
}

export default function ProjectsPage() {
  const [search, setSearch] = useState("")
  const [projects, setProjects] = useState<ProjectItem[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [editingProject, setEditingProject] = useState<ProjectItem | null>(null)
  const { toast } = useToast()

  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [techStack, setTechStack] = useState("")

  useEffect(() => {
    fetchProjects()
  }, [])

  const fetchProjects = async () => {
    try {
      const { data } = await api.get("/projects")
      const items = data?.items || []
      setProjects(items)
    } catch {
      setProjects([])
    } finally {
      setLoading(false)
    }
  }

  const resetForm = () => {
    setName("")
    setDescription("")
    setTechStack("")
    setEditingProject(null)
  }

  const handleCreate = async () => {
    if (!name.trim()) {
      toast("destructive", "Project name is required")
      return
    }
    setSubmitting(true)
    try {
      await api.post("/projects", {
        name: name.trim(),
        description: description.trim() || undefined,
        tech_stack: techStack.split(",").map((t) => t.trim()).filter(Boolean),
      })
      toast("success", `Project "${name}" created`)
      resetForm()
      setOpen(false)
      fetchProjects()
    } catch (e: any) {
      toast("destructive", e.response?.data?.detail || "Failed to create project")
    } finally {
      setSubmitting(false)
    }
  }

  const handleUpdate = async () => {
    if (!editingProject || !name.trim()) return
    setSubmitting(true)
    try {
      await api.put(`/projects/${editingProject.id}`, {
        name: name.trim(),
        description: description.trim() || undefined,
        tech_stack: techStack.split(",").map((t) => t.trim()).filter(Boolean),
      })
      toast("success", `Project "${name}" updated`)
      resetForm()
      setOpen(false)
      fetchProjects()
    } catch (e: any) {
      toast("destructive", e.response?.data?.detail || "Failed to update project")
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (project: ProjectItem) => {
    if (!confirm(`Delete "${project.name}"? This cannot be undone.`)) return
    try {
      await api.delete(`/projects/${project.id}`)
      toast("success", `Project "${project.name}" deleted`)
      fetchProjects()
    } catch (e: any) {
      toast("destructive", e.response?.data?.detail || "Failed to delete project")
    }
  }

  const openEdit = (project: ProjectItem) => {
    setName(project.name)
    setDescription(project.description || "")
    setTechStack(project.tech_stack.join(", "))
    setEditingProject(project)
    setOpen(true)
  }

  const openCreate = () => {
    resetForm()
    setOpen(true)
  }

  const filtered = projects.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-5 max-w-5xl mx-auto">
      <Breadcrumbs items={[{ label: "Projects" }]} />
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Projects</h1>
          <p className="text-sm text-muted-foreground mt-1">Manage all your software projects</p>
        </div>
        <Dialog open={open} onOpenChange={(v) => { if (!v) resetForm(); setOpen(v) }}>
          <DialogTrigger asChild>
            <Button size="sm" onClick={openCreate}>
              <Plus className="w-4 h-4" />
              Add Project
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{editingProject ? "Edit Project" : "Create New Project"}</DialogTitle>
              <DialogDescription>
                {editingProject ? "Update project details." : "Set up a new project for the AI to work on."}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div>
                <label className="text-sm font-medium text-foreground mb-1.5 block">Name *</label>
                <Input placeholder="e.g., E-commerce Platform" value={name}
                  onChange={(e) => setName(e.target.value)} />
              </div>
              <div>
                <label className="text-sm font-medium text-foreground mb-1.5 block">Description</label>
                <Textarea placeholder="Describe the project..." value={description}
                  onChange={(e) => setDescription(e.target.value)} rows={3} />
              </div>
              <div>
                <label className="text-sm font-medium text-foreground mb-1.5 block">Tech Stack</label>
                <Input placeholder="e.g., React, Python, PostgreSQL" value={techStack}
                  onChange={(e) => setTechStack(e.target.value)} />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => { resetForm(); setOpen(false) }}>Cancel</Button>
              <Button onClick={editingProject ? handleUpdate : handleCreate} disabled={submitting || !name.trim()}>
                {submitting ? "Saving..." : editingProject ? "Update" : "Create"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </motion.div>

      <div className="flex gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input placeholder="Search projects..." value={search}
            onChange={(e) => setSearch(e.target.value)} className="pl-9" />
        </div>
      </div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24" />)}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((project, i) => (
            <motion.div key={project.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}>
              <Card className="card-hover">
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="space-y-1 min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <Briefcase className="w-4 h-4 text-primary shrink-0" />
                      <p className="font-medium text-foreground truncate">{project.name}</p>
                    </div>
                    {project.description && (
                      <p className="text-sm text-muted-foreground line-clamp-1">{project.description}</p>
                    )}
                    {project.tech_stack.length > 0 && (
                      <div className="flex gap-1.5 flex-wrap mt-1">
                        {project.tech_stack.slice(0, 5).map((tech) => (
                          <Badge key={tech} variant="outline" className="text-xs">{tech}</Badge>
                        ))}
                        {project.tech_stack.length > 5 && (
                          <Badge variant="outline" className="text-xs">+{project.tech_stack.length - 5}</Badge>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-4">
                    <Badge variant={STATUS_COLORS[project.status] || "neutral"}>{project.status}</Badge>
                    <Button variant="ghost" size="icon" onClick={() => openEdit(project)}>
                      <Edit2 className="w-3.5 h-3.5" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => handleDelete(project)}>
                      <Trash2 className="w-3.5 h-3.5 text-destructive" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
          {filtered.length === 0 && (
            <div className="text-center py-12 text-muted-foreground text-sm">
              {projects.length === 0 ? "No projects yet. Click 'Add Project' to create one." : "No projects match your search."}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
