import React from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { 
  Home, 
  FolderOpen, 
  Users, 
  DollarSign, 
  BarChart3, 
  Settings,
  LogOut 
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const Layout = ({ children, title }) => {
  const { user, logout, isAdmin } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const navigation = isAdmin 
    ? [
        { name: '대시보드', href: '/admin', icon: Home },
        { name: '프로젝트', href: '/admin/projects', icon: FolderOpen },
        { name: '사용자', href: '/admin/users', icon: Users },
        { name: '노무단가', href: '/admin/labor-costs', icon: DollarSign },
        { name: '리포트', href: '/admin/reports', icon: BarChart3 },
      ]
    : [
        { name: '내 프로젝트', href: '/dashboard', icon: Home },
      ]

  const isCurrentPath = (path) => location.pathname === path

  return (
    <div className="flex h-screen bg-gray-900">
      {/* Sidebar */}
      <div className="hidden md:flex md:w-64 md:flex-col">
        <div className="flex flex-col flex-grow pt-5 bg-gray-800 overflow-y-auto">
          <div className="flex items-center flex-shrink-0 px-4">
            <h1 className="text-xl font-bold text-white">노무비 관리</h1>
          </div>
          
          <div className="mt-8 flex-1 flex flex-col">
            <nav className="flex-1 px-2 pb-4 space-y-1">
              {navigation.map((item) => {
                const Icon = item.icon
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors ${
                      isCurrentPath(item.href)
                        ? 'bg-gray-700 text-white'
                        : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                    }`}
                  >
                    <Icon className="mr-3 h-5 w-5 flex-shrink-0" />
                    {item.name}
                  </Link>
                )
              })}
            </nav>
          </div>

          {/* User info */}
          <div className="flex-shrink-0 flex border-t border-gray-700 p-4">
            <div className="flex-shrink-0 w-full group block">
              <div className="flex items-center">
                <div className="ml-3 flex-1">
                  <p className="text-sm font-medium text-white">
                    {user?.username}
                  </p>
                  <p className="text-xs text-gray-400">
                    {user?.role === 'admin' ? '관리자' : '사용자'}
                  </p>
                </div>
                <button
                  onClick={handleLogout}
                  className="ml-3 p-1 rounded-full text-gray-400 hover:text-white transition-colors"
                  title="로그아웃"
                >
                  <LogOut className="h-5 w-5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-col flex-1 overflow-hidden">
        <header className="bg-gray-800 shadow-sm border-b border-gray-700">
          <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
            <h2 className="text-2xl font-bold text-white">{title}</h2>
          </div>
        </header>

        <main className="flex-1 relative overflow-y-auto focus:outline-none">
          <div className="py-6">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              {children}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

export default Layout