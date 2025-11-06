Param(
  [Parameter(Position=0)]
  [string]$Cmd = "help"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Run-Tests { pytest -q }
function Run-Lint {
  ruff check .
  $savedPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    bandit -r scripts -ll | Out-Host
    # Ignore exit code (matches bash "|| true" behavior)
  } catch {
    # Continue execution even if bandit fails
  } finally {
    $ErrorActionPreference = $savedPreference
  }
}
function Run-Format {
  ruff format .
  black .
}
function Run-Audit {
  $savedPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    pip-audit --strict | Out-Host
    # Ignore exit code (matches bash "|| true" behavior)
  } catch {
    # Continue execution even if pip-audit fails
  } finally {
    $ErrorActionPreference = $savedPreference
  }
}
function Run-Generate { python scripts/generate_lists.py --formats adguard ublock hosts }

switch ($Cmd) {
  "test" { Run-Tests }
  "lint" { Run-Lint }
  "fmt" { Run-Format }
  "format" { Run-Format }
  "audit" { Run-Audit }
  "gen" { Run-Generate }
  "generate" { Run-Generate }
  Default {
    Write-Host "Usage: .\\tasks.ps1 [test|lint|format|audit|generate]"
  }
}


