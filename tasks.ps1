Param(
  [Parameter(Position=0)]
  [string]$Cmd = "help"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Run-Tests { pytest -q }
function Run-Lint {
  ruff check .
  bandit -r scripts -ll | Out-Host
}
function Run-Format {
  ruff format .
  black .
}
function Run-Audit { pip-audit --strict | Out-Host }
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


