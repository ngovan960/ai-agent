"use client"

import * as React from "react"
import {
  ToastProvider as ShadcnProvider,
  ToastViewport,
  Toast,
  ToastTitle,
  ToastDescription,
  ToastClose,
} from "@/components/ui/toast"

type ToastVariant = "default" | "success" | "destructive"

interface ToastItem {
  id: string
  title: string
  variant: ToastVariant
}

interface ToastContextValue {
  toast: (variant: ToastVariant, title: string) => void
}

const ToastContext = React.createContext<ToastContextValue | null>(null)

export function useToast() {
  const ctx = React.useContext(ToastContext)
  if (!ctx) throw new Error("useToast must be used within ToastProvider")
  return ctx
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastItem[]>([])

  const addToast = React.useCallback((variant: ToastVariant, title: string) => {
    const id = Math.random().toString(36).slice(2)
    setToasts((prev) => [...prev, { id, variant, title }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 4000)
  }, [])

  return (
    <ToastContext.Provider value={{ toast: addToast }}>
      <ShadcnProvider>
        {children}
        {toasts.map((t) => (
          <Toast key={t.id} variant={t.variant === "success" ? "success" : t.variant === "destructive" ? "destructive" : "default"}>
            <div className="flex flex-col gap-1">
              <ToastTitle>{t.title}</ToastTitle>
            </div>
            <ToastClose />
          </Toast>
        ))}
        <ToastViewport />
      </ShadcnProvider>
    </ToastContext.Provider>
  )
}
