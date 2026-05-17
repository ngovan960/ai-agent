import axios from "axios"

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
  timeout: 10000,
  headers: { "Content-Type": "application/json" },
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error("API Error:", err.response?.data || err.message)
    return Promise.reject(err)
  },
)

export async function fetchSummary() {
  const { data } = await api.get("/dashboard/summary")
  return data
}

export async function fetchTasksByStatus() {
  const { data } = await api.get("/dashboard/tasks-by-status")
  return data
}

export async function fetchCostBreakdown() {
  const { data } = await api.get("/dashboard/cost-breakdown")
  return data
}

export async function fetchRecentActivity(limit = 10) {
  const { data } = await api.get(`/dashboard/recent-activity?limit=${limit}`)
  return data
}

export async function fetchInstructions(params: Record<string, any> = {}) {
  const { data } = await api.get("/instructions", { params })
  return data
}

export async function fetchDecisions(params: Record<string, any> = {}) {
  const { data } = await api.get("/decisions", { params })
  return data
}

export default api
