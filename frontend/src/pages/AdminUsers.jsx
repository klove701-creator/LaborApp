import React from 'react'
import Layout from '../components/Layout'

const AdminUsers = () => {
  return (
    <Layout title="사용자 관리">
      <div className="card">
        <div className="p-8 text-center">
          <h3 className="text-lg font-medium text-white mb-4">사용자 관리</h3>
          <p className="text-gray-400">사용자 생성, 수정, 삭제 및 권한 관리 기능이 구현될 예정입니다.</p>
        </div>
      </div>
    </Layout>
  )
}

export default AdminUsers