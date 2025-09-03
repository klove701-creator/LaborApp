import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'

// Components
import LoadingSpinner from './components/LoadingSpinner'
import ProtectedRoute from './components/ProtectedRoute'

// Pages
import LoginPage from './pages/LoginPage'
import UserDashboard from './pages/UserDashboard'
import ProjectDetail from './pages/ProjectDetail'
import AdminDashboard from './pages/AdminDashboard'
import AdminProjects from './pages/AdminProjects'
import AdminUsers from './pages/AdminUsers'
import AdminLaborCosts from './pages/AdminLaborCosts'
import AdminReports from './pages/AdminReports'

function App() {
  const { loading, isAuthenticated, isAdmin } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <LoadingSpinner size="large" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900">
      <Routes>
        {/* Public Routes */}
        <Route
          path="/login"
          element={
            isAuthenticated ? (
              <Navigate to={isAdmin ? "/admin" : "/dashboard"} replace />
            ) : (
              <LoginPage />
            )
          }
        />

        {/* User Routes */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <UserDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/project/:projectName"
          element={
            <ProtectedRoute>
              <ProjectDetail />
            </ProtectedRoute>
          }
        />

        {/* Admin Routes */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute requireAdmin>
              <AdminDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/projects"
          element={
            <ProtectedRoute requireAdmin>
              <AdminProjects />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/users"
          element={
            <ProtectedRoute requireAdmin>
              <AdminUsers />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/labor-costs"
          element={
            <ProtectedRoute requireAdmin>
              <AdminLaborCosts />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/reports"
          element={
            <ProtectedRoute requireAdmin>
              <AdminReports />
            </ProtectedRoute>
          }
        />

        {/* Default Redirects */}
        <Route
          path="/"
          element={
            <Navigate
              to={
                isAuthenticated
                  ? isAdmin
                    ? "/admin"
                    : "/dashboard"
                  : "/login"
              }
              replace
            />
          }
        />

        {/* 404 */}
        <Route
          path="*"
          element={
            <div className="min-h-screen bg-gray-900 flex items-center justify-center">
              <div className="text-center text-white">
                <h1 className="text-4xl font-bold mb-4">404</h1>
                <p className="text-gray-400">페이지를 찾을 수 없습니다.</p>
              </div>
            </div>
          }
        />
      </Routes>
    </div>
  )
}

export default App