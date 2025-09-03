# database.py - Supabase PostgreSQL 연결 (안정화 버전)
import os
import psycopg2
import json
import time
from datetime import datetime, date
from psycopg2.extras import RealDictCursor
from psycopg2 import OperationalError, DatabaseError

class DatabaseManager:
    def __init__(self):
        # Supabase 연결 정보
        self.database_url = os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL 환경변수가 설정되지 않았습니다.")
        
        # 연결 설정
        self.conn = None
        self.max_retries = 3
        self.retry_delay = 1  # 초
        self.connect()
    
    def connect(self):
        """데이터베이스 연결 (재시도 로직 포함)"""
        for attempt in range(self.max_retries):
            try:
                # 기존 연결 정리
                if self.conn and not self.conn.closed:
                    self.conn.close()
                
                # 새 연결 생성
                self.conn = psycopg2.connect(
                    self.database_url,
                    cursor_factory=RealDictCursor,
                    connect_timeout=10,  # 연결 타임아웃
                    application_name='LaborApp'  # 앱 식별자
                )
                # 자동 커밋 비활성화
                self.conn.autocommit = False
                
                # 스키마 경로 설정 및 연결 테스트
                with self.conn.cursor() as cur:
                    cur.execute("SET search_path TO public")
                    cur.execute("SELECT 1")  # 연결 테스트
                    self.conn.commit()
                
                print(f"✅ Supabase PostgreSQL 연결 성공 (시도 {attempt + 1})")
                return
                
            except Exception as e:
                print(f"❌ 연결 시도 {attempt + 1} 실패: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    self.retry_delay *= 2  # 지수 백오프
                else:
                    raise ConnectionError(f"데이터베이스 연결 최종 실패: {e}")
    
    def get_connection(self):
        """안전한 연결 확인 및 반환 (최적화)"""
        try:
            # 연결 상태만 빠르게 확인 (테스트 쿼리 제거)
            if self.conn is None or self.conn.closed != 0:
                self.connect()
            return self.conn
        except (OperationalError, DatabaseError):
            # 한 번만 재연결 시도
            self.connect()
            return self.conn
    
    def execute_query(self, query, params=None, fetch=False):
        """안전한 쿼리 실행"""
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                conn = self.get_connection()
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    
                    if fetch:
                        if fetch == 'all':
                            result = cur.fetchall()
                        elif fetch == 'one':
                            result = cur.fetchone()
                        else:
                            result = cur.fetchmany(fetch)
                    else:
                        result = None
                    
                    conn.commit()
                    return result
                    
            except (OperationalError, DatabaseError) as e:
                print(f"쿼리 실행 실패 (시도 {attempt + 1}): {e}")
                if attempt < max_attempts - 1:
                    self.conn = None
                    time.sleep(0.5)
                else:
                    raise
    
    # ===== 사용자 관리 =====
    def get_users(self):
        """모든 사용자 조회"""
        try:
            rows = self.execute_query("""
                SELECT username, password, role, status, created_date, projects
                FROM public.users
            """, fetch='all')
            
            users_data = {}
            for row in rows or []:
                users_data[row['username']] = {
                    'password': row['password'],
                    'role': row['role'],
                    'status': row['status'],
                    'created_date': str(row['created_date']) if row['created_date'] else '',
                    'projects': row['projects'] or []
                }
            return users_data
            
        except Exception as e:
            print(f"❌ 사용자 조회 실패: {e}")
            return {}
    
    def create_user(self, username, password, role='user', projects=None, status='active'):
        """사용자 생성"""
        try:
            self.execute_query("""
                INSERT INTO public.users (username, password, role, projects, status)
                VALUES (%s, %s, %s, %s, %s)
            """, (username, password, role, projects or [], status))
            print(f"✅ 사용자 생성 성공: {username}")
        except Exception as e:
            print(f"❌ 사용자 생성 실패: {e}")
            raise
    
    def update_user(self, old_username, new_username=None, password=None, 
                    role=None, projects=None, status=None):
        """사용자 정보 업데이트"""
        try:
            updates = []
            values = []
            
            if new_username and new_username != old_username:
                updates.append("username = %s")
                values.append(new_username)
            if password:
                updates.append("password = %s")
                values.append(password)
            if role:
                updates.append("role = %s")
                values.append(role)
            if projects is not None:
                updates.append("projects = %s")
                values.append(projects)
            if status:
                updates.append("status = %s")
                values.append(status)
            
            if updates:
                query = f"UPDATE public.users SET {', '.join(updates)} WHERE username = %s"
                values.append(old_username)
                self.execute_query(query, values)
                print(f"✅ 사용자 업데이트 성공: {old_username}")
                
        except Exception as e:
            print(f"❌ 사용자 업데이트 실패: {e}")
            raise
    
    def delete_user(self, username):
        """사용자 삭제"""
        try:
            self.execute_query("DELETE FROM public.users WHERE username = %s", (username,))
            print(f"✅ 사용자 삭제 성공: {username}")
        except Exception as e:
            print(f"❌ 사용자 삭제 실패: {e}")
            raise
    
    # ===== 프로젝트 관리 =====
    def get_projects(self):
        """모든 프로젝트 조회"""
        try:
            rows = self.execute_query("""
                SELECT project_name, status, created_date, work_types, contracts, companies
                FROM public.projects
            """, fetch='all')
            
            projects_data = {}
            for row in rows or []:
                projects_data[row['project_name']] = {
                    'status': row['status'],
                    'created_date': str(row['created_date']) if row['created_date'] else '',
                    'work_types': row['work_types'] or [],
                    'contracts': row['contracts'] or {},
                    'companies': row['companies'] or {},
                    'daily_data': self._get_project_daily_data(row['project_name'])
                }
            return projects_data
            
        except Exception as e:
            print(f"❌ 프로젝트 조회 실패: {e}")
            return {}
    
    def _get_project_daily_data(self, project_name):
        """프로젝트의 일일 데이터 조회 (인덱스 최적화)"""
        try:
            # 최신 30일만 조회하여 성능 개선
            rows = self.execute_query("""
                SELECT work_date, work_type, day_workers, night_workers, 
                       midnight_workers, total_workers, progress
                FROM public.daily_data 
                WHERE project_name = %s 
                  AND work_date >= CURRENT_DATE - INTERVAL '30 days'
                ORDER BY work_date DESC, work_type
            """, (project_name,), fetch='all')
            
            daily_data = {}
            for row in rows or []:
                date_str = str(row['work_date'])
                if date_str not in daily_data:
                    daily_data[date_str] = {}
                
                daily_data[date_str][row['work_type']] = {
                    'day': row['day_workers'],
                    'night': row['night_workers'],
                    'midnight': row['midnight_workers'],
                    'total': row['total_workers'],
                    'progress': float(row['progress']) if row['progress'] else 0.0
                }
            return daily_data
            
        except Exception as e:
            print(f"❌ 일일 데이터 조회 실패 ({project_name}): {e}")
            return {}
    
    def create_project(self, project_name, work_types, contracts=None, 
                      companies=None, status='active'):
        """프로젝트 생성"""
        try:
            self.execute_query("""
                INSERT INTO public.projects (project_name, work_types, contracts, companies, status)
                VALUES (%s, %s, %s, %s, %s)
            """, (project_name, work_types, 
                  json.dumps(contracts or {}), 
                  json.dumps(companies or {}), 
                  status))
            print(f"✅ 프로젝트 생성 성공: {project_name}")
        except Exception as e:
            print(f"❌ 프로젝트 생성 실패: {e}")
            raise
    
    def update_project(self, project_name, **kwargs):
        """프로젝트 업데이트"""
        try:
            updates = []
            values = []
            
            for key, value in kwargs.items():
                if key in ['work_types', 'contracts', 'companies']:
                    updates.append(f"{key} = %s")
                    values.append(json.dumps(value) if key in ['contracts', 'companies'] else value)
                elif key in ['status']:
                    updates.append(f"{key} = %s")
                    values.append(value)
            
            if updates:
                query = f"UPDATE public.projects SET {', '.join(updates)} WHERE project_name = %s"
                values.append(project_name)
                self.execute_query(query, values)
                print(f"✅ 프로젝트 업데이트 성공: {project_name}")
                
        except Exception as e:
            print(f"❌ 프로젝트 업데이트 실패: {e}")
            raise
    
    def delete_project(self, project_name):
        """프로젝트 및 관련 일일 데이터 삭제"""
        try:
            # 일일 데이터 먼저 삭제
            self.execute_query("DELETE FROM public.daily_data WHERE project_name = %s", (project_name,))
            # 프로젝트 삭제
            self.execute_query("DELETE FROM public.projects WHERE project_name = %s", (project_name,))
            print(f"✅ 프로젝트 삭제 성공: {project_name}")
        except Exception as e:
            print(f"❌ 프로젝트 삭제 실패: {e}")
            raise
    
    # ===== 일일 데이터 관리 =====
    def save_daily_data(self, project_name, work_date, work_type, 
                       day_workers, night_workers, midnight_workers, progress=0.0):
        """일일 출역 데이터 저장/업데이트"""
        try:
            total_workers = day_workers + night_workers + midnight_workers
            
            self.execute_query("""
                INSERT INTO public.daily_data 
                (project_name, work_date, work_type, day_workers, night_workers, 
                 midnight_workers, total_workers, progress, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (project_name, work_date, work_type)
                DO UPDATE SET
                    day_workers = EXCLUDED.day_workers,
                    night_workers = EXCLUDED.night_workers,
                    midnight_workers = EXCLUDED.midnight_workers,
                    total_workers = EXCLUDED.total_workers,
                    progress = EXCLUDED.progress,
                    updated_at = NOW()
            """, (project_name, work_date, work_type, day_workers, 
                  night_workers, midnight_workers, total_workers, progress))
            
            print(f"✅ 일일 데이터 저장 성공: {project_name} - {work_type} - {work_date}")
            
        except Exception as e:
            print(f"❌ 일일 데이터 저장 실패: {e}")
            raise
    
    # ===== 노무단가 관리 =====
    def get_labor_costs(self):
        """모든 노무단가 조회"""
        try:
            rows = self.execute_query("""
                SELECT work_type, day_cost, night_cost, midnight_cost, locked
                FROM public.labor_costs
            """, fetch='all')
            
            labor_costs = {}
            for row in rows or []:
                labor_costs[row['work_type']] = {
                    'day': row['day_cost'],
                    'night': row['night_cost'],
                    'midnight': row['midnight_cost'],
                    'locked': row['locked']
                }
            return labor_costs
            
        except Exception as e:
            print(f"❌ 노무단가 조회 실패: {e}")
            return {}
    
    def save_labor_cost(self, work_type, day_cost, night_cost, midnight_cost, locked=False):
        """노무단가 저장/업데이트"""
        try:
            self.execute_query("""
                INSERT INTO public.labor_costs (work_type, day_cost, night_cost, midnight_cost, locked)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (work_type)
                DO UPDATE SET
                    day_cost = EXCLUDED.day_cost,
                    night_cost = EXCLUDED.night_cost,
                    midnight_cost = EXCLUDED.midnight_cost,
                    locked = EXCLUDED.locked
            """, (work_type, day_cost, night_cost, midnight_cost, locked))
            print(f"✅ 노무단가 저장 성공: {work_type}")
        except Exception as e:
            print(f"❌ 노무단가 저장 실패: {e}")
            raise
    
    def delete_labor_cost(self, work_type):
        """노무단가 삭제"""
        try:
            self.execute_query("DELETE FROM public.labor_costs WHERE work_type = %s", (work_type,))
            print(f"✅ 노무단가 삭제 성공: {work_type}")
        except Exception as e:
            print(f"❌ 노무단가 삭제 실패: {e}")
            raise
    
    def close(self):
        """데이터베이스 연결 종료"""
        try:
            if self.conn and not self.conn.closed:
                self.conn.close()
                print("✅ 데이터베이스 연결 종료")
        except Exception as e:
            print(f"연결 종료 중 오류: {e}")