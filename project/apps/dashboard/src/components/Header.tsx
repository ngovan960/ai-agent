"use client"

import { Search, Moon, Sun, Bell } from "lucide-react"
import { useState } from "react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { useTheme } from "@/lib/theme"
import { usePathname } from "next/navigation"

const PAGE_TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/tasks": "Tasks",
  "/audit": "Audit Logs",
  "/agents": "Agents",
  "/cost": "Cost Analysis",
  "/memory": "Memory",
  "/alerts": "Alerts",
  "/workflow": "Workflow",
}

export default function Header() {
  const pathname = usePathname()
  const { theme, toggleTheme } = useTheme()
  const [searchOpen, setSearchOpen] = useState(false)

  return (
    <header className="flex items-center justify-between px-4 lg:px-6 h-16 border-b bg-card shrink-0">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-semibold text-foreground hidden sm:block">
          {PAGE_TITLES[pathname] || "Dashboard"}
        </h1>
      </div>
      <div className="flex items-center gap-2">
        {searchOpen && (
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input placeholder="Search..." className="w-48 pl-9 h-9 text-sm" autoFocus onBlur={() => setSearchOpen(false)} />
          </div>
        )}
        <Button variant="ghost" size="icon" onClick={() => setSearchOpen(!searchOpen)} className="text-muted-foreground">
          <Search className="w-4 h-4" />
        </Button>
        <Button variant="ghost" size="icon" className="text-muted-foreground">
          <Bell className="w-4 h-4" />
        </Button>
        <Button variant="ghost" size="icon" onClick={toggleTheme} className="text-muted-foreground">
          {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </Button>
      </div>
    </header>
  )
}
