#!/bin/bash
# Railway 배포용 빌드 스크립트

echo "🔧 LaborApp 통합 빌드 시작..."

# Node.js와 npm이 있는지 확인
if ! command -v node &> /dev/null; then
    echo "❌ Node.js가 설치되지 않았습니다."
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ npm이 설치되지 않았습니다."
    exit 1
fi

echo "📦 Python 의존성 설치..."
pip install -r requirements.txt

echo "📦 React 의존성 설치..."
cd frontend
npm install

echo "🏗️ React 앱 빌드..."
npm run build

echo "✅ 빌드 완료!"
echo "   - Python 백엔드: Flask 앱"
echo "   - React 프론트엔드: frontend/dist/"

cd ..
echo "🚀 배포 준비 완료!"