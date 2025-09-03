import React from 'react'
import Layout from '../components/Layout'

const AdminProjects = () => {
  return (
    <Layout title="프로젝트 관리">
      <div className="card">
        <div className="p-8 text-center">
          <h3 className="text-lg font-medium text-white mb-4">프로젝트 관리</h3>
          <p className="text-gray-400">프로젝트 생성, 수정, 삭제 기능이 구현될 예정입니다.</p>
        </div>
      </div>
    </Layout>
  )
}

export default AdminProjects