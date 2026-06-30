Push-Location "c:\Users\AnilN\Documents\capstone_project\Capstone_project_ai\contract-analysis-tool\backend"

# Read .env file and set environment variables
$envFile = ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            # Skip comments and empty lines
            if ($key -and -not $key.StartsWith("#")) {
                [System.Environment]::SetEnvironmentVariable($key, $value, [System.EnvironmentVariableTarget]::Process)
            }
        }
    }
    Write-Host "Loaded .env configuration"
}

# Runtime mode:
# - Default: use DATABASE_URL from .env (e.g., Supabase/Postgres)
# - Optional local mode: set USE_LOCAL_SQLITE=true before running script
$useLocalSqlite = ($env:USE_LOCAL_SQLITE -eq "true")

if ($useLocalSqlite) {
    $env:DATABASE_URL = "sqlite+aiosqlite:///./app.db"
    Write-Host "Database mode: local SQLite (USE_LOCAL_SQLITE=true)"
} else {
    # For Supabase + asyncpg, ensure SSL query parameter is compatible.
    if ($env:DATABASE_URL -and $env:DATABASE_URL.Contains("supabase.com") -and ($env:DATABASE_URL -notmatch "ssl=require")) {
        if ($env:DATABASE_URL.Contains("?")) {
            $env:DATABASE_URL = "$($env:DATABASE_URL)&ssl=require"
        } else {
            $env:DATABASE_URL = "$($env:DATABASE_URL)?ssl=require"
        }
    }
    Write-Host "Database mode: DATABASE_URL from .env"
}

# Keep local-friendly runtime defaults for queue/storage unless explicitly changed in environment.
$env:REDIS_URL = ""
$env:CELERY_BROKER_URL = ""
$env:CELERY_RESULT_BACKEND = ""
$env:S3_ENDPOINT_URL = ""
$env:USE_LOCAL_STORAGE_FALLBACK = "true"
$env:LOCAL_STORAGE_DIR = "./local_storage"

Write-Host "LiteLLM Config: PROXY_URL=$($env:LITELLM_PROXY_URL), Model=$($env:LLM_MODEL)"

C:/Users/AnilN/AppData/Local/Programs/Python/Python314/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Pop-Location
