import React from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from 'react-query'
import { Calendar, Users, TrendingUp, AlertTriangle } from 'lucide-react'

import Layout from '../components/Layout'
import LoadingSpinner from '../components/LoadingSpinner'
import { useAuth } from '../contexts/AuthContext'
import apiService from '../services/api'

const UserDashboard = () => {
  const { user } = useAuth()

  const { data: projects, isLoading } = useQuery(
    'user-projects',
    apiService.getProjects,
    {
      staleTime: 1 * 60 * 1000, // 1 minute
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
        return <TrendingUp className="h-4 w-4" />
      default:
        return null
    }
  }

  if (isLoading) {
    return (
      <Layout title="내 프로젝트">
        <div className="flex justify-center py-12">
          <LoadingSpinner size="large" />
        </div>
      </Layout>
    )
  }

  const userProjects = user?.projects || []
  const filteredProjects = Object.entries(projects || {}).filter(
    ([projectName]) => userProjects.includes(projectName)
  )

  return (
    <Layout title="내 프로젝트">
      <div className="space-y-6">
        {/* Stats overview */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-primary-500 rounded-md flex items-center justify-center">
                  <Users className="h-4 w-4 text-white" />
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-400">할당된 프로젝트</p>
                <p className="text-2xl font-semibold text-white">{filteredProjects.length}</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-success-500 rounded-md flex items-center justify-center">
                  <TrendingUp className="h-4 w-4 text-white" />
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-400">활성 프로젝트</p>
                <p className="text-2xl font-semibold text-white">
                  {filteredProjects.filter(([, project]) => project.status === 'active').length}
                </p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-warning-500 rounded-md flex items-center justify-center">
                  <Calendar className="h-4 w-4 text-white" />
                </div>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-400">오늘 날짜</p>
                <p className="text-lg font-semibold text-white">
                  {new Date().toLocaleDateString('ko-KR')}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Projects list */}
        <div className="card">
          <div className="px-6 py-4 border-b border-gray-700">
            <h3 className="text-lg font-medium text-white">프로젝트 목록</h3>
          </div>
          
          {filteredProjects.length === 0 ? (
            <div className="px-6 py-8 text-center">
              <p className="text-gray-400">할당된 프로젝트가 없습니다.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-700">
              {filteredProjects.map(([projectName, project]) => {
                // Calculate basic stats from daily data
                const dailyData = project.daily_data || {}
                const dates = Object.keys(dailyData)
                const recentDate = dates.length > 0 ? Math.max(...dates) : null
                const todayData = recentDate ? dailyData[recentDate] || {} : {}
                
                const todayWorkers = Object.values(todayData).reduce(
                  (sum, workData) => sum + (workData.total || 0), 0
                )

                return (
                  <Link
                    key={projectName}
                    to={`/project/${encodeURIComponent(projectName)}`}
                    className="block hover:bg-gray-750 transition-colors"
                  >
                    <div className="px-6 py-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3">
                            <h4 className="text-lg font-medium text-white">
                              {projectName}
                            </h4>
                            <span className={`${getStatusColor('양호')} inline-flex items-center space-x-1`}>
                              {getStatusIcon('양호')}
                              <span>양호</span>
                            </span>
                          </div>
                          
                          <div className="mt-2 flex items-center space-x-6 text-sm text-gray-400">
                            <span>공종: {project.work_types?.length || 0}개</span>
                            <span>최근 활동: {recentDate || '데이터 없음'}</span>
                            <span>오늘 투입: {todayWorkers}명</span>
                          </div>
                        </div>
                        
                        <div className="flex-shrink-0 text-gray-400">
                          <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                          </svg>
                        </div>
                      </div>
                    </div>
                  </Link>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </Layout>
  )
}

export default UserDashboard