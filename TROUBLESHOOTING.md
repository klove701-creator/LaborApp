# Troubleshooting

- Error: "API 엔드포인트를 찾을 수 없습니다."
  - Meaning: The backend returned 404 JSON from the API.
  - Common causes:
    - VITE_API_URL includes a trailing "/api" causing double prefix (e.g., /api/api/...)
    - VITE_API_URL is missing (defaults to localhost:5000) in production
    - Backend process is not `api_app.py` or is on a different port
    - Calling a non-existent route or wrong HTTP method
  - Fix:
    - Frontend `.env`: set `VITE_API_URL` to the origin only (no `/api`)
      - Example: `VITE_API_URL=kiyenolabor.up.railway.app`
    - Dev check: `curl http://localhost:5000/api/health`
    - Frontend runtime: in browser console check `import.meta.env.VITE_API_URL` and `apiService.client.defaults.baseURL`
    - Ensure backend runs `api_app.py` (not legacy `app.py`)
