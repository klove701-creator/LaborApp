import axios from 'axios'
import toast from 'react-hot-toast'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

class ApiService {
  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}/api`,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('token')
          localStorage.removeItem('user')
          window.location.href = '/login'
          return Promise.reject(error)
        }

        const message = error.response?.data?.error || '서버 오류가 발생했습니다.'
        toast.error(message)
        return Promise.reject(error)
      }
    )
  }

  // Auth
  async login(username, password) {
    const response = await this.client.post('/auth/login', { username, password })
    return response.data
  }

  async getCurrentUser() {
    const response = await this.client.get('/auth/me')
    return response.data
  }

  // Projects
  async getProjects() {
    const response = await this.client.get('/projects')
    return response.data.projects
  }

  async getProjectDetail(projectName) {
    const response = await this.client.get(`/projects/${projectName}`)
    return response.data.project
  }

  async getProjectSummary(projectName, date = null) {
    const params = date ? { date } : {}
    const response = await this.client.get(`/projects/${projectName}/summary`, { params })
    return response.data
  }

  async saveDailyData(projectName, date, workData) {
    const response = await this.client.post(`/projects/${projectName}/daily-data`, {
      date,
      work_data: workData
    })
    return response.data
  }

  async getProjectDatesWithData(projectName, month = null) {
    const params = month ? { month } : {}
    const response = await this.client.get(`/projects/${projectName}/dates-with-data`, { params })
    return response.data.dates
  }

  async addWorkTypeToProject(projectName, workType) {
    const response = await this.client.post(`/projects/${projectName}/work-types`, {
      work_type: workType
    })
    return response.data
  }

  // Admin - Dashboard
  async getAdminDashboard() {
    const response = await this.client.get('/admin/dashboard')
    return response.data.dashboard
  }

  // Admin - Projects
  async createProject(projectData) {
    const response = await this.client.post('/admin/projects', projectData)
    return response.data
  }

  async updateProject(projectName, projectData) {
    const response = await this.client.put(`/admin/projects/${projectName}`, projectData)
    return response.data
  }

  async deleteProject(projectName) {
    const response = await this.client.delete(`/admin/projects/${projectName}`)
    return response.data
  }

  // Admin - Users
  async getUsers() {
    const response = await this.client.get('/admin/users')
    return response.data.users
  }

  async createUser(userData) {
    const response = await this.client.post('/admin/users', userData)
    return response.data
  }

  async updateUser(username, userData) {
    const response = await this.client.put(`/admin/users/${username}`, userData)
    return response.data
  }

  async deleteUser(username) {
    const response = await this.client.delete(`/admin/users/${username}`)
    return response.data
  }

  // Labor Costs
  async getLaborCosts() {
    const response = await this.client.get('/labor-costs')
    return response.data.labor_costs
  }

  async saveLaborCost(laborCostData) {
    const response = await this.client.post('/admin/labor-costs', laborCostData)
    return response.data
  }

  // Utilities
  async getAvailableWorkTypes() {
    const response = await this.client.get('/available-work-types')
    return response.data.work_types
  }

  async checkWorkTypeSimilarity(workType) {
    const response = await this.client.post('/work-type-similarity', { work_type: workType })
    return response.data
  }

  // Reports
  async getProjectWorkSummary(projectName) {
    const response = await this.client.get('/admin/reports/project-summary', {
      params: { project: projectName }
    })
    return response.data.summary
  }
}

export const apiService = new ApiService()
export default apiService