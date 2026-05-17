"use client"

import { LayoutDashboard, CheckSquare2, FileText, Bot, DollarSign, BookOpen, AlertTriangle, Workflow, ChevronLeft, ChevronRight, Briefcase, ShieldCheck } from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { useState } from "react"
import { Button } from "@/components/ui/button"

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/projects", label: "Projects", icon: Briefcase },
  { href: "/tasks", label: "Tasks", icon: CheckSquare2 },
  { href: "/audit", label: "Audit Logs", icon: FileText },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/approvals", label: "Approvals", icon: ShieldCheck },
  { href: "/cost", label: "Cost", icon: DollarSign },
  { href: "/memory", label: "Memory", icon: BookOpen },
  { href: "/alerts", label: "Alerts", icon: AlertTriangle },
  { href: "/workflow", label: "Workflow", icon: Workflow },
]

export default function Sidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside className={cn(
      "flex flex-col border-r bg-card transition-all duration-300",
      collapsed ? "w-16" : "w-60"
    )}>
      <div className="flex items-center gap-3 px-4 h-16 border-b shrink-0">
        <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shrink-0">
          <span className="text-primary-foreground font-bold text-sm">AI</span>
        </div>
        {!collapsed && (
          <span className="font-semibold text-foreground truncate">SDLC Orchestrator</span>
        )}
      </div>
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/" && pathname.startsWith(href))
          return (
            <Link key={href} href={href}>
              <div className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150",
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}>
                <Icon className="w-5 h-5 shrink-0" />
                {!collapsed && <span className="truncate">{label}</span>}
              </div>
            </Link>
          )
        })}
      </nav>
      <div className="p-3 border-t">
        <Button variant="ghost" size="sm" className="w-full justify-center" onClick={() => setCollapsed(!collapsed)}>
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </Button>
      </div>
    </aside>
  )
}
