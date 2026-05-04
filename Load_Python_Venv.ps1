try {
    & .\.venv\Scripts\Activate.ps1
}
catch {
    Write-Warning "Failed to activate venv. Make sure it exists in .\.venv"
}
