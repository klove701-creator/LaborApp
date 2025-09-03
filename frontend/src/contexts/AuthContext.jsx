import React, { createContext, useContext, useState, useEffect } from 'react'
import apiService from '../services/api'
import toast from 'react-hot-toast'

const AuthContext = createContext({})

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const token = localStorage.getItem('token')
        const storedUser = localStorage.getItem('user')

        if (token && storedUser) {
          setUser(JSON.parse(storedUser))
          // Verify token validity
          try {
            const currentUser = await apiService.getCurrentUser()
            setUser(currentUser)
            localStorage.setItem('user', JSON.stringify(currentUser))
          } catch (error) {
            // Token is invalid
            logout()
          }
        }
      } catch (error) {
        console.error('Auth initialization failed:', error)
      } finally {
        setLoading(false)
      }
    }

    initializeAuth()
  }, [])

  const login = async (username, password) => {
    try {
      const response = await apiService.login(username, password)
      const { access_token, user: userData } = response

      localStorage.setItem('token', access_token)
      localStorage.setItem('user', JSON.stringify(userData))
      setUser(userData)

      toast.success(`환영합니다, ${userData.username}님!`)
      return userData
    } catch (error) {
      const message = error.response?.data?.error || '로그인에 실패했습니다.'
      toast.error(message)
      throw error
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
    toast.success('로그아웃되었습니다.')
  }

  const value = {
    user,
    loading,
    login,
    logout,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin',
    isUser: user?.role === 'user',
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}