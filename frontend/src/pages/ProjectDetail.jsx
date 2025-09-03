import React, { useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { format, parseISO } from 'date-fns'
import { ko } from 'date-fns/locale'

import Layout from '../components/Layout'
import LoadingSpinner from '../components/LoadingSpinner'
import apiService from '../services/api'
import toast from 'react-hot-toast'

const ProjectDetail = () => {
  const { projectName } = useParams()
  const queryClient = useQueryClient()
  const decodedProjectName = decodeURIComponent(projectName)
  const [selectedDate, setSelectedDate] = useState(
    new Date().toISOString().split('T')[0]
  )
  const [workData, setWorkData] = useState({})
  const [isOptimisticUpdate, setIsOptimisticUpdate] = useState(false)

  const { data: project, isLoading: projectLoading } = useQuery(
    ['project', decodedProjectName],
    () => apiService.getProjectDetail(decodedProjectName)
  )

  const { data: summary, isLoading: summaryLoading } = useQuery(
    ['project-summary', decodedProjectName, selectedDate],
    () => apiService.getProjectSummary(decodedProjectName, selectedDate)
  )

  const saveMutation = useMutation(
    (data) => apiService.saveDailyData(decodedProjectName, selectedDate, data),
    {
      onMutate: async (newData) => {
        // Optimistic update
        setIsOptimisticUpdate(true)
        
        // Cancel any outgoing refetches
        await queryClient.cancelQueries(['project-summary', decodedProjectName, selectedDate])
        
        // Snapshot the previous value
        const previousSummary = queryClient.getQueryData(['project-summary', decodedProjectName, selectedDate])
        
        // Optimistically update the summary
        queryClient.setQueryData(['project-summary', decodedProjectName, selectedDate], (old) => {
          if (!old) return old
          
          // Calculate optimistic totals
          let totalToday = 0
          let totalCumulative = old.totals?.cumulative || 0
          
          Object.values(newData).forEach(work => {
            totalToday += (work.day || 0) + (work.night || 0) + (work.midnight || 0)
          })
          
          return {
            ...old,
            totals: {
              ...old.totals,
              today: totalToday,
              cumulative: totalCumulative + totalToday
            }
          }
        })
        
        toast.success('저장중...', { duration: 1000 })
        return { previousSummary }
      },
      onError: (err, newData, context) => {
        // Revert optimistic update
        queryClient.setQueryData(
          ['project-summary', decodedProjectName, selectedDate], 
          context.previousSummary
        )
        toast.error('저장에 실패했습니다.')
      },
      onSuccess: () => {
        toast.success('데이터가 저장되었습니다.')
        queryClient.invalidateQueries(['project-summary', decodedProjectName, selectedDate])
      },
      onSettled: () => {
        setIsOptimisticUpdate(false)
      }
    }
  )

  const handleInputChange = useCallback((workType, field, value) => {
    setWorkData(prev => ({
      ...prev,
      [workType]: {
        ...prev[workType],
        [field]: parseInt(value) || 0
      }
    }))
  }, [])

  const handleSave = () => {
    if (Object.keys(workData).length === 0) {
      toast.error('변경된 데이터가 없습니다.')
      return
    }
    saveMutation.mutate(workData)
  }

  if (projectLoading) {
    return (
      <Layout title={decodedProjectName}>
        <div className="flex justify-center py-12">
          <LoadingSpinner size="large" />
        </div>
      </Layout>
    )
  }

  if (!project) {
    return (
      <Layout title="프로젝트">
        <div className="text-center py-12">
          <p className="text-gray-400">프로젝트를 찾을 수 없습니다.</p>
        </div>
      </Layout>
    )
  }

  return (
    <Layout title={decodedProjectName}>
      <div className="space-y-6">
        {/* Date selector */}
        <div className="card">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-white">작업 일지 입력</h3>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="input max-w-48"
            />
          </div>
        </div>

        {/* Work types input */}
        <div className="card">
          <div className="px-6 py-4 border-b border-gray-700">
            <h4 className="text-md font-medium text-white">공종별 투입 인원</h4>
          </div>
          
          {project.work_types?.length === 0 ? (
            <div className="px-6 py-8 text-center">
              <p className="text-gray-400">등록된 공종이 없습니다.</p>
            </div>
          ) : (
            <div className="p-6 space-y-4">
              {project.work_types?.map((workType) => {
                const dailyData = project.daily_data?.[selectedDate]?.[workType] || {}
                
                return (
                  <div key={workType} className="border border-gray-700 rounded-lg p-4">
                    <h5 className="text-white font-medium mb-3">{workType}</h5>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <label className="block text-sm text-gray-400 mb-1">주간</label>
                        <input
                          type="number"
                          min="0"
                          defaultValue={dailyData.day || 0}
                          className="input"
                          placeholder="0"
                          onChange={(e) => handleInputChange(workType, 'day', e.target.value)}
                        />
                      </div>
                      <div>
                        <label className="block text-sm text-gray-400 mb-1">야간</label>
                        <input
                          type="number"
                          min="0"
                          defaultValue={dailyData.night || 0}
                          className="input"
                          placeholder="0"
                          onChange={(e) => handleInputChange(workType, 'night', e.target.value)}
                        />
                      </div>
                      <div>
                        <label className="block text-sm text-gray-400 mb-1">심야</label>
                        <input
                          type="number"
                          min="0"
                          defaultValue={dailyData.midnight || 0}
                          className="input"
                          placeholder="0"
                          onChange={(e) => handleInputChange(workType, 'midnight', e.target.value)}
                        />
                      </div>
                      <div>
                        <label className="block text-sm text-gray-400 mb-1">공정율(%)</label>
                        <input
                          type="number"
                          min="0"
                          max="100"
                          step="0.1"
                          defaultValue={dailyData.progress || 0}
                          className="input"
                          placeholder="0"
                          onChange={(e) => handleInputChange(workType, 'progress', e.target.value)}
                        />
                      </div>
                    </div>
                  </div>
                )
              })}
              
              <div className="flex justify-end pt-4">
                <button
                  onClick={handleSave}
                  disabled={saveMutation.isLoading || isOptimisticUpdate}
                  className={`btn-primary ${isOptimisticUpdate ? 'opacity-75' : ''}`}
                >
                  {saveMutation.isLoading || isOptimisticUpdate ? (
                    <LoadingSpinner size="small" />
                  ) : (
                    '저장'
                  )}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Summary */}
        {summaryLoading ? (
          <div className="card">
            <div className="flex justify-center py-8">
              <LoadingSpinner />
            </div>
          </div>
        ) : summary && (
          <div className="card">
            <div className="px-6 py-4 border-b border-gray-700">
              <h4 className="text-md font-medium text-white">프로젝트 현황</h4>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center">
                  <p className="text-2xl font-bold text-white">{summary.totals?.today || 0}</p>
                  <p className="text-sm text-gray-400">오늘 투입</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-white">{summary.totals?.cumulative || 0}</p>
                  <p className="text-sm text-gray-400">누계 투입</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-white">{summary.health?.meta?.progress_rate || 0}%</p>
                  <p className="text-sm text-gray-400">진행율</p>
                </div>
                <div className="text-center">
                  <span className={`status-${summary.health?.color || 'success'} text-lg`}>
                    {summary.health?.status || '양호'}
                  </span>
                  <p className="text-sm text-gray-400">상태</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}

export default ProjectDetail