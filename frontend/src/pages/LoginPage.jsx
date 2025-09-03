import React, { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useForm } from 'react-hook-form'
import LoadingSpinner from '../components/LoadingSpinner'

const LoginPage = () => {
  const { login, isAuthenticated, isAdmin } = useAuth()
  const [loading, setLoading] = useState(false)
  
  const {
    register,
    handleSubmit,
    formState: { errors }
  } = useForm()

  if (isAuthenticated) {
    return <Navigate to={isAdmin ? "/admin" : "/dashboard"} replace />
  }

  const onSubmit = async (data) => {
    setLoading(true)
    try {
      await login(data.username, data.password)
    } catch (error) {
      // Error is handled in context
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="max-w-md w-full space-y-8 px-4">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-white">
            노무비 관리 시스템
          </h2>
          <p className="mt-2 text-center text-sm text-gray-400">
            계정에 로그인하세요
          </p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit(onSubmit)}>
          <div className="space-y-4">
            <div>
              <label htmlFor="username" className="sr-only">
                사용자명
              </label>
              <input
                {...register('username', { required: '사용자명을 입력해주세요' })}
                type="text"
                className="input"
                placeholder="사용자명"
                disabled={loading}
              />
              {errors.username && (
                <p className="mt-1 text-sm text-red-400">{errors.username.message}</p>
              )}
            </div>
            
            <div>
              <label htmlFor="password" className="sr-only">
                비밀번호
              </label>
              <input
                {...register('password', { required: '비밀번호를 입력해주세요' })}
                type="password"
                className="input"
                placeholder="비밀번호"
                disabled={loading}
              />
              {errors.password && (
                <p className="mt-1 text-sm text-red-400">{errors.password.message}</p>
              )}
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full flex justify-center py-3"
            >
              {loading ? <LoadingSpinner size="small" /> : '로그인'}
            </button>
          </div>
        </form>

        <div className="text-center text-sm text-gray-500">
          <p>관리자: admin / 사용자: user 계정으로 접근</p>
        </div>
      </div>
    </div>
  )
}

export default LoginPage