<#
.SYNOPSIS
    Test runner for Task-Oriented UI Framework.

.DESCRIPTION
    Wraps pytest with convenient options. All modes use the .venv Python.

.PARAMETER All
    Run the full test suite (default).

.PARAMETER Fast
    Run only fast tests — excludes Qt tests and slow (sleep) tests.
    Safe to run on every save.

.PARAMETER Module
    Run tests for a specific module path under tests/.
    Examples: "framework/core"  |  "ui"  |  "bootstrap"

.PARAMETER Filter
    Run tests whose name matches the given keyword (-k flag).
    Example: "cleanup"  |  "is_alive"  |  "CLITask"

.PARAMETER Coverage
    Attach coverage reporting (--cov + --cov-report=term-missing).

.PARAMETER Html
    Produce an HTML coverage report in htmlcov/.

.PARAMETER Verbose
    Pass -v to pytest for per-test output.

.PARAMETER FailFast
    Stop at first failure (-x).

.EXAMPLE
    # Full suite with coverage
    .\run_tests.ps1 -Coverage

.EXAMPLE
    # Fast feedback during development (no Qt, no sleep)
    .\run_tests.ps1 -Fast

.EXAMPLE
    # Only run tests related to cleanup
    .\run_tests.ps1 -Filter cleanup

.EXAMPLE
    # Only framework/core module tests with verbose output
    .\run_tests.ps1 -Module framework/core -Verbose

.EXAMPLE
    # Full suite + HTML coverage report
    .\run_tests.ps1 -Coverage -Html
#>
param(
    [switch]$All,
    [switch]$Fast,
    [string]$Module    = "",
    [string]$Filter    = "",
    [switch]$Coverage,
    [switch]$Html,
    [switch]$Verbose,
    [switch]$FailFast
)

$ErrorActionPreference = "Stop"
$PY   = ".\.venv\Scripts\python.exe"
$ROOT = $PSScriptRoot

if (-not (Test-Path $PY)) {
    Write-Error "Virtual environment not found at $PY. Run: python -m venv .venv && pip install -e .[dev]"
    exit 1
}

# ── Build target path ────────────────────────────────────────────────────────
$target = "tests"
if ($Module -ne "") {
    $target = "tests/$Module"
}

# ── Build pytest args ────────────────────────────────────────────────────────
$pytestArgs = @($target)

if ($Fast) {
    $pytestArgs += "-m", "not qt and not slow"
    Write-Host "⚡ Fast mode — skipping Qt and slow tests" -ForegroundColor Cyan
}

if ($Filter -ne "") {
    $pytestArgs += "-k", $Filter
    Write-Host "🔍 Filter: '$Filter'" -ForegroundColor Cyan
}

if ($Coverage -or $Html) {
    $pytestArgs += "--cov=framework", "--cov=ui", "--cov=app", "--cov-report=term-missing"
    if ($Html) {
        $pytestArgs += "--cov-report=html:htmlcov"
    }
}

if ($Verbose) {
    $pytestArgs += "-v"
} else {
    # Always show one-line summary per test result
    $pytestArgs += "-ra"
}

if ($FailFast) {
    $pytestArgs += "-x"
}

# ── Run ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "══════════════════════════════════════════" -ForegroundColor DarkGray
Write-Host " Running: pytest $($pytestArgs -join ' ')" -ForegroundColor White
Write-Host "══════════════════════════════════════════" -ForegroundColor DarkGray
Write-Host ""

& $PY -m pytest @pytestArgs
$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "✅ All tests passed." -ForegroundColor Green
} else {
    Write-Host "❌ Some tests failed (exit code $exitCode)." -ForegroundColor Red
}

if ($Html -and $exitCode -eq 0) {
    Write-Host "📊 HTML coverage report: $ROOT\htmlcov\index.html" -ForegroundColor Cyan
}

exit $exitCode
