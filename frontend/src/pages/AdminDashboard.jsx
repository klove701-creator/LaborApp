import React from 'react'
import { useQuery } from 'react-query'
import { 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle, 
  Users, 
  FolderOpen, 
  DollarSign,
  Activity 
} from 'lucide-react'

import Layout from '../components/Layout'
import LoadingSpinner from '../components/LoadingSpinner'
import apiService from '../services/api'

const AdminDashboard = () => {
  const { data: dashboard, isLoading } = useQuery(
    'admin-dashboard',
    apiService.getAdminDashboard,
    {
      refetchInterval: 30000, // 30 seconds
    }
  )

  const getStatusColor = (status) => {
    switch (status) {
      case '양호':
        return 'status-success'
      case '경고':
        return 'status-warning'
      case '위험':
        return 'status-danger'
      default:
        return 'status-success'
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case '위험':
        return <AlertTriangle className="h-4 w-4" />
      case '경고':
        return <TrendingDown className="h-4 w-4" />
      case '양호':
        return <TrendingUp className="h-4 w-4" />
      default:
        return <Activity className="h-4 w-4" />
    }
  }

  if (isLoading) {
    return (
      <Layout title="관리자 대시보드">
        <div className="flex justify-center py-12">
          <LoadingSpinner size="large" />
        </div>
      </Layout>
    )
  }

  const stats = {
    totalProjects: dashboard?.length || 0,
    activeProjects: dashboard?.filter(p => p.status !== 'inactive').length || 0,
    riskProjects: dashboard?.filter(p => p.status === '위험').length || 0,
    warningProjects: dashboard?.filter(p => p.status === '경고').length || 0,
  }

  return (
    <Layout title="관리자 대시보드">
      <div className="space-y-6">
        {/* Stats overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-primary-500 rounded-md flex items-center justify-center">
                  <FolderOpen className="h-4 w-4 text-white" />
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-400">전체 프로젝트</p>
                <p className="text-2xl font-semibold text-white">{stats.totalProjects}</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-success-500 rounded-md flex items-center justify-center">
                  <Activity className="h-4 w-4 text-white" />
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-400">활성 프로젝트</p>
                <p className="text-2xl font-semibold text-white">{stats.activeProjects}</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-warning-500 rounded-md flex items-center justify-center">
                  <TrendingDown className="h-4 w-4 text-white" />
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-400">주의 프로젝트</p>
                <p className="text-2xl font-semibold text-white">{stats.warningProjects}</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-danger-500 rounded-md flex items-center justify-center">
                  <AlertTriangle className="h-4 w-4 text-white" />
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-400">위험 프로젝트</p>
                <p className="text-2xl font-semibold text-white">{stats.riskProjects}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Projects overview */}
        <div className="card">
          <div className="px-6 py-4 border-b border-gray-700">
            <h3 className="text-lg font-medium text-white">프로젝트 현황</h3>
          </div>
          
          {dashboard?.length === 0 ? (
            <div className="px-6 py-8 text-center">
              <p className="text-gray-400">프로젝트가 없습니다.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-700">
                <thead className="bg-gray-750">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      프로젝트명
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      상태
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      오늘 투입
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      누계 투입
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      진행률
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      공정률
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      최근 활동
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {dashboard?.map((project) => (
                    <tr key={project.project_name} className="hover:bg-gray-750 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-white">
                          {project.project_name}
                        </div>
                        <div className="text-sm text-gray-400">
                          {project.work_count}개 공종
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`${getStatusColor(project.status)} inline-flex items-center space-x-1`}>
                          {getStatusIcon(project.status)}
                          <span>{project.status}</span>
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                        {project.today_workers?.toLocaleString() || 0}명
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                        {project.cumulative_workers?.toLocaleString() || 0}명
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                        {project.avg_progress?.toFixed(1) || 0}%
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                        {project.schedule_rate?.toFixed(1) || 0}%
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">
                        {project.recent_date}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </Layout>
  )
}

export default AdminDashboard