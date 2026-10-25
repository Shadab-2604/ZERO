# Zero AI Windows Setup & Verification Script
param(
    [switch]$SkipPlaywright = $false,
    [switch]$SkipSmokeTests = $false
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " ZERO AI // WINDOWS INSTALLATION & ENVIRONMENT SETUP" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Project Root: $ProjectRoot`n"

# Step 1: Detect Python 3.11+
Write-Host "[1/7] Checking Python runtime..." -ForegroundColor Yellow
$PythonExe = $null

$VenvDir = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

if (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
    Write-Host "  [OK] Found existing virtual environment Python: $VenvPython" -ForegroundColor Green
} else {
    try {
        $ver = & python --version 2>&1
        if ($ver -match "Python (\d+)\.(\d+)") {
            if ([int]$matches[1] -eq 3 -and [int]$matches[2] -ge 11) {
                $PythonExe = "python"
                Write-Host "  [OK] Found compatible system Python: $ver" -ForegroundColor Green
            }
        }
    } catch {
        $null = $_
    }

    if (-not $PythonExe) {
        try {
            $ver = & py -3 --version 2>&1
            if ($ver -match "Python (\d+)\.(\d+)") {
                if ([int]$matches[1] -eq 3 -and [int]$matches[2] -ge 11) {
                    $PythonExe = "py"
                    Write-Host "  [OK] Found compatible Python launcher: $ver" -ForegroundColor Green
                }
            }
        } catch {
            $null = $_
        }
    }
}

if (-not $PythonExe) {
    Write-Host "  [FAIL] ERROR: Python 3.11+ is required but was not found." -ForegroundColor Red
    Write-Host "    Please install Python 3.11 or 3.12 from https://www.python.org/downloads/windows/" -ForegroundColor Red
    Write-Host "    Make sure to check 'Add Python to PATH' during installation." -ForegroundColor Yellow
    exit 1
}

# Step 2: Ensure Virtual Environment (.venv)
Write-Host "`n[2/7] Verifying project virtual environment (.venv)..." -ForegroundColor Yellow
if (-not (Test-Path $VenvPython)) {
    Write-Host "  -> Creating local virtual environment at: $VenvDir" -ForegroundColor Gray
    & $PythonExe -m venv $VenvDir
    Write-Host "  [OK] Virtual environment created." -ForegroundColor Green
} else {
    Write-Host "  [OK] Virtual environment verified." -ForegroundColor Green
}

# Step 3: Upgrade pip and install dependencies
Write-Host "`n[3/7] Installing project dependencies..." -ForegroundColor Yellow
$ReqFile = Join-Path $ProjectRoot "requirements.txt"
if (Test-Path $ReqFile) {
    Write-Host "  -> Running pip install from requirements.txt..." -ForegroundColor Gray
    & $VenvPython -m pip install --upgrade pip --quiet
    & $VenvPython -m pip install -r $ReqFile --quiet
    Write-Host "  [OK] Python dependencies successfully installed." -ForegroundColor Green
} else {
    Write-Host "  [FAIL] requirements.txt not found at $ReqFile" -ForegroundColor Red
    exit 1
}

# Step 4: Install Playwright Chromium Browser
if (-not $SkipPlaywright) {
    Write-Host "`n[4/7] Checking Playwright Chromium browser for PDF generation..." -ForegroundColor Yellow
    try {
        & $VenvPython -m playwright install chromium
        Write-Host "  [OK] Playwright Chromium browser installed and verified." -ForegroundColor Green
    } catch {
        Write-Host "  [WARN] Notice: Playwright browser setup notice: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n[4/7] Skipping Playwright installation (-SkipPlaywright flag)." -ForegroundColor Gray
}

# Step 5: Create Required Local Directories
Write-Host "`n[5/7] Ensuring local directory structure..." -ForegroundColor Yellow
$RequiredDirs = @(
    (Join-Path $ProjectRoot "Knowledge"),
    (Join-Path $ProjectRoot "data"),
    (Join-Path $ProjectRoot "exports"),
    (Join-Path $ProjectRoot "logs"),
    (Join-Path $ProjectRoot "scripts"),
    (Join-Path $ProjectRoot "tests")
)

foreach ($dir in $RequiredDirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  + Created: $dir" -ForegroundColor Green
    } else {
        Write-Host "  [OK] Exists : $dir" -ForegroundColor Gray
    }
}

# Step 6: Verify .env Configuration File
Write-Host "`n[6/7] Validating environment configuration (.env)..." -ForegroundColor Yellow
$EnvFile = Join-Path $ProjectRoot ".env"
$EnvExample = Join-Path $ProjectRoot ".env.example"

if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Copy-Item -Path $EnvExample -Destination $EnvFile
        Write-Host "  + Generated initial .env from template (.env.example)" -ForegroundColor Yellow
        Write-Host "    (Zero runs in offline Demo mode by default; add an API key in Settings when ready.)" -ForegroundColor Gray
    } else {
        Write-Host "  [WARN] .env and .env.example are missing." -ForegroundColor Yellow
    }
} else {
    Write-Host "  [OK] .env configuration present (Existing credentials and settings preserved)." -ForegroundColor Green
}

# Step 7: Run System Doctor & Smoke Diagnostics
if (-not $SkipSmokeTests) {
    Write-Host "`n[7/7] Executing system diagnostics (doctor.py)..." -ForegroundColor Yellow
    $DoctorScript = Join-Path $ProjectRoot "scripts\doctor.py"
    if (Test-Path $DoctorScript) {
        & $VenvPython $DoctorScript
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n[OK] All doctor diagnostics passed successfully." -ForegroundColor Green
        } else {
            Write-Host "`n[WARN] Doctor completed with non-zero status. Review logs above." -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "`n[7/7] Skipping smoke tests (-SkipSmokeTests flag)." -ForegroundColor Gray
}

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host " SETUP COMPLETE! Zero AI is ready to launch." -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "To launch the Zero desktop assistant:" -ForegroundColor White
Write-Host "  .\.venv\Scripts\python.exe main.py`n" -ForegroundColor Yellow
Write-Host "Available maintenance commands:" -ForegroundColor White
Write-Host "  .\.venv\Scripts\python.exe scripts\doctor.py" -ForegroundColor Gray
Write-Host "  .\.venv\Scripts\python.exe scripts\test_knowledge.py" -ForegroundColor Gray
Write-Host "  .\.venv\Scripts\python.exe scripts\reindex_knowledge.py" -ForegroundColor Gray
Write-Host "  .\.venv\Scripts\python.exe scripts\test_pdf_export.py" -ForegroundColor Gray
Write-Host "  .\.venv\Scripts\pytest.exe -v`n" -ForegroundColor Gray
