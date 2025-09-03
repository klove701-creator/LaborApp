# Database Connection Fix Steps

## Current Issue
Password authentication failed for user "postgres" on Supabase connection.

## Current Connection String (from logs)
```
postgresql://postgres.wrrxyiblfxawxurchdhs:Knkkjy701!@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres
```

## Fix Steps

### 1. Get Correct Connection String from Supabase
1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Go to Settings → Database
4. Find "Connection String" section
5. Copy the "Connection Pooling" string

### 2. Expected Format
```
postgresql://postgres.wrrxyiblfxawxurchdhs:[YOUR_ACTUAL_PASSWORD]@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres?sslmode=require
```

### 3. Update Railway Environment Variable
1. Go to Railway Dashboard
2. Select your LaborApp project
3. Go to Variables tab
4. Update `DATABASE_URL` with correct connection string
5. Click Deploy

### 4. Alternative: Direct Connection (if pooling fails)
```
postgresql://postgres:[YOUR_ACTUAL_PASSWORD]@db.wrrxyiblfxawxurchdhs.supabase.co:5432/postgres
```

## Test After Update
Run this command to test the connection:
```bash
python simple_db_test.py
```

Expected success output:
```
SUCCESS: Connected to PostgreSQL
Version: PostgreSQL 15.1 on x86_64-pc-linux-gnu...
Database: postgres
User: postgres
```

## Common Issues

### Password with Special Characters
If password contains special characters like `!@#$%`, they need URL encoding:
- `!` becomes `%21`
- `@` becomes `%40`
- `#` becomes `%23`
- `$` becomes `%24`
- `%` becomes `%25`

### SSL Mode
Add `?sslmode=require` at the end of connection string if needed.

## Verification
After fixing DATABASE_URL in Railway:
1. Check Railway deployment logs
2. Visit `/health` endpoint - should show `database: "connected"`
3. Test API endpoints that require database access