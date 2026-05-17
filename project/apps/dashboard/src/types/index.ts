export interface DashboardSummary {
  projects: number
  tasks: number
  active_tasks: number
  instructions: number
  decisions: number
  total_cost: number
}

export interface TaskStatusCount {
  status: string
  count: number
}

export interface CostItem {
  model: string
  cost: number
}

export interface Activity {
  id?: string
  action: string
  actor: string
  result: string
  message?: string
  created_at: string
}

export interface TaskItem {
  id: string
  title: string
  status: string
  priority: string
  owner?: string
  confidence?: number
  project_id: string
  created_at?: string
  description?: string
}

export interface ProjectItem {
  id: string
  name: string
  description: string | null
  status: string
  created_at: string
  tech_stack: string[]
}

export interface Alert {
  id: number
  severity: "info" | "warning" | "error"
  message: string
}

export interface Agent {
  name: string
  task: string
  status: "idle" | "working"
  calls: number
}

export interface WorkflowNode {
  id: string
  x: number
  label: string
  color: string
  y?: number
}

export interface WorkflowEdge {
  from: string
  to: string
}
