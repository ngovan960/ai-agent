"use client"

import { AlertTriangle, Info, XCircle, X } from "lucide-react"
import { motion } from "framer-motion"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

interface AlertBannerProps {
  severity: "info" | "warning" | "error"
  message: string
  onDismiss?: () => void
}

const VARIANTS = {
  error: { bg: "bg-destructive/5 border-destructive/20", icon: XCircle, color: "text-destructive" },
  warning: { bg: "bg-warning-50 border-warning-200", icon: AlertTriangle, color: "text-warning-600" },
  info: { bg: "bg-muted border-border", icon: Info, color: "text-muted-foreground" },
}

export default function AlertBanner({ severity, message, onDismiss }: AlertBannerProps) {
  const v = VARIANTS[severity]
  const Icon = v.icon

  return (
    <motion.div layout className={cn("flex items-start gap-3 rounded-lg border px-4 py-3", v.bg)}>
      <Icon className={cn("w-5 h-5 mt-0.5 shrink-0", v.color)} />
      <p className="flex-1 text-sm text-foreground">{message}</p>
      {onDismiss && (
        <Button variant="ghost" size="icon" className="w-6 h-6 -mr-1 -mt-0.5" onClick={onDismiss}>
          <X className="w-3.5 h-3.5" />
        </Button>
      )}
    </motion.div>
  )
}
