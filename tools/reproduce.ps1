<#
.SYNOPSIS
    Reproduce the whole study from a clean checkout with one command.

.DESCRIPTION
    Runs the three reproduction steps from docs/compliance-check.md 5.1 and the four
    pre-submit self-checks from AGENTS.md 5, in one go, and stops at the first failure.

        self-checks        python -m unittest discover -s tests -q
                           python -m govern.run --selftest
                           python tools/scan_secrets.py
                           python -m govern.provenance --check
        reproduction       python -m experiments.run --config conditions.yaml
                           python -m analysis.run --runs <out>/runs --run-id E-REPRO

    Everything it writes goes to a fresh directory: the run logs, the result table,
    the figures and one transcript per step. It never writes to the repository's own
    runs/ or analysis/, never deletes anything, and never overwrites an existing file.

    Offline by construction: replay mode needs no network and no API key. The script
    does not read -- and will not print -- any environment variable that could hold one.

    The experiment configuration is used exactly as committed (conditions.yaml, twelve
    cells, one participant). This script does not change the conditions, the task set or
    the number of repetitions; if you want a different scope, edit conditions.yaml and
    say so in your own record.

.PARAMETER OutDir
    Where to write everything. Default: _repro\<UTC timestamp>. Must not already exist.

.PARAMETER Python
    The interpreter to use. Default: python (the repository's own runtime; no venv needed,
    because the runtime has no third-party dependencies).

.EXAMPLE
    pwsh -File tools/reproduce.ps1

.EXAMPLE
    pwsh -File tools/reproduce.ps1 -OutDir _repro\try-1
#>
[CmdletBinding()]
param(
    [string]$OutDir = "",
    [string]$Python = "python"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")
if ([string]::IsNullOrWhiteSpace($OutDir)) {
    $OutDir = Join-Path $Root ("_repro\" + $Stamp)
}
$OutDir = [System.IO.Path]::GetFullPath($OutDir)
$LogDir = Join-Path $OutDir "logs"
$RunRoot = Join-Path $OutDir "runs"
$AnalysisDir = Join-Path $OutDir "analysis"
$RunId = "E-REPRO"

# --- guards: never write into the user's data, never overwrite -----------------------
foreach ($forbidden in @((Join-Path $Root "runs"), (Join-Path $Root "analysis"))) {
    $full = [System.IO.Path]::GetFullPath($forbidden)
    if ($OutDir -eq $full -or $OutDir.StartsWith($full + [System.IO.Path]::DirectorySeparatorChar)) {
        Write-Host "refused: -OutDir must not be inside $forbidden" -ForegroundColor Red
        Write-Host "This script writes a new run and a new workbook; pointing it at the project's own"
        Write-Host "runs/ or analysis/ would overwrite data you may want to keep."
        exit 2
    }
}
if (Test-Path -LiteralPath $OutDir) {
    Write-Host "refused: $OutDir already exists" -ForegroundColor Red
    Write-Host "Nothing was written. Pass a new -OutDir, or leave it out to get a timestamped one."
    exit 2
}
foreach ($needed in @("conditions.yaml", "config\config.json", "govern", "experiments", "analysis")) {
    if (-not (Test-Path -LiteralPath (Join-Path $Root $needed))) {
        Write-Host "refused: $needed is missing; run this from a full checkout" -ForegroundColor Red
        exit 2
    }
}

New-Item -ItemType Directory -Path $OutDir, $LogDir, $RunRoot, $AnalysisDir -Force | Out-Null

$Script:Results = @()
$StepNumber = 0

function Invoke-Step {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Slug,
        [Parameter(Mandatory)][string[]]$Arguments
    )
    $script:StepNumber++
    $label = "{0}. {1}" -f $script:StepNumber, $Name
    Write-Host ""
    Write-Host ("== " + $label) -ForegroundColor Cyan
    Write-Host ("   {0} {1}" -f $Python, ($Arguments -join " ")) -ForegroundColor DarkGray

    $logPath = Join-Path $LogDir ("{0:d2}-{1}.log" -f $script:StepNumber, $Slug)
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    # Windows PowerShell 5.1 turns a native command's stderr into a terminating error when
    # $ErrorActionPreference is Stop. The exit code is the signal we act on, so drop to
    # Continue for the call and restore afterwards.
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    # Run each step from the checkout root, not from wherever the caller happened to be:
    # relative arguments (conditions.yaml, runs\) must resolve the same way every time.
    Push-Location -LiteralPath $Root
    try {
        $output = & $Python @Arguments 2>&1
        $code = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
    $ErrorActionPreference = $previous
    $watch.Stop()

    ($output | ForEach-Object { "$_" }) | Tee-Object -FilePath $logPath | ForEach-Object { "   $_" }

    $script:Results += [ordered]@{
        step      = $label
        command   = "$Python $($Arguments -join ' ')"
        exit_code = $code
        seconds   = [math]::Round($watch.Elapsed.TotalSeconds, 1)
        log       = $logPath.Substring($OutDir.Length + 1)
    }

    if ($code -ne 0) {
        Write-Host ""
        Write-Host ("FAILED at step {0}: {1}" -f $script:StepNumber, $Name) -ForegroundColor Red
        Write-Host ("   exit code {0}; transcript: {1}" -f $code, $logPath) -ForegroundColor Red
        Write-Host "   Nothing was hidden: the steps after this one did not run."
        Save-Summary -Ok $false
        exit $code
    }
}

function Save-Summary {
    param([bool]$Ok)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $version = (& $Python --version 2>&1 | Out-String).Trim()
    $ErrorActionPreference = $previous
    $summary = [ordered]@{
        ok         = $Ok
        started_at = $script:StartedAt
        ended_at   = (Get-Date).ToUniversalTime().ToString("o")
        out_dir    = $OutDir
        python     = $version
        host_os    = [System.Environment]::OSVersion.VersionString
        run_id     = $RunId
        steps      = $script:Results
    }
    $text = ($summary | ConvertTo-Json -Depth 5)
    # UTF-8 without a BOM: Set-Content -Encoding UTF8 adds one on PowerShell 5.1, and a
    # BOM makes the file stop being valid JSON for everything that reads it next.
    [System.IO.File]::WriteAllText((Join-Path $OutDir "reproduce.json"), $text, (New-Object System.Text.UTF8Encoding($false)))
}

$script:StartedAt = (Get-Date).ToUniversalTime().ToString("o")

Write-Host "reproduce: three reproduction steps and four self-checks" -ForegroundColor White
Write-Host "  interpreter : $Python"
Write-Host "  writes to   : $OutDir"
Write-Host "  run id      : $RunId (logical name only; lives under the output directory)"
Write-Host "  not touched : runs\, analysis\, dist\, recordings\, corpus\ (all read-only here)"
Write-Host "  offline     : replay mode; no network, no API key, no environment variable read"

# --- self-checks (AGENTS.md 5, items 1-4) -------------------------------------------
Invoke-Step -Name "self-check: standard-library test suite" -Slug "unittest" `
    -Arguments @("-m", "unittest", "discover", "-s", "tests", "-q")
Invoke-Step -Name "self-check: six tasks, six cards" -Slug "selftest" `
    -Arguments @("-m", "govern.run", "--selftest")
Invoke-Step -Name "self-check: no secrets or endpoints in the tree" -Slug "scan-secrets" `
    -Arguments @("tools\scan_secrets.py")
Invoke-Step -Name "self-check: provenance ledger covers every module" -Slug "provenance" `
    -Arguments @("-m", "govern.provenance", "--check")

# --- the three reproduction steps (compliance-check 5.1) ----------------------------
# Step 1 of 5.1 is the same self-test run above, so it is not repeated here; steps 2 and 3
# are pointed at the isolated output directory instead of runs/ and analysis/.
Invoke-Step -Name "reproduce: run both conditions over the same task set" -Slug "experiments" `
    -Arguments @("-m", "experiments.run", "--config", "conditions.yaml",
                 "--runs-root", $RunRoot, "--run-id", $RunId)
Invoke-Step -Name "reproduce: rebuild the result table and figures from those logs" -Slug "analysis" `
    -Arguments @("-m", "analysis.run", "--runs", $RunRoot, "--run-id", $RunId, "--out", $AnalysisDir)

# --- only now is anything called a success ------------------------------------------
$workbook = Join-Path $AnalysisDir "results.xlsx"
$figures = @(Get-ChildItem -LiteralPath (Join-Path $AnalysisDir "figures") -Filter *.png -ErrorAction SilentlyContinue)
$logs = @(Get-ChildItem -LiteralPath (Join-Path (Join-Path $RunRoot $RunId) "logs") -Recurse -Filter *.jsonl -ErrorAction SilentlyContinue)

if (-not (Test-Path -LiteralPath $workbook)) {
    Write-Host ""
    Write-Host "FAILED after the last step: the workbook was not written" -ForegroundColor Red
    Save-Summary -Ok $false
    exit 1
}

Save-Summary -Ok $true

Write-Host ""
Write-Host ("ok: {0} of {0} steps passed" -f $script:StepNumber) -ForegroundColor Green
Write-Host ("    session logs : {0} jsonl files under {1}" -f $logs.Count, $RunRoot)
Write-Host ("    workbook     : $workbook")
Write-Host ("    figures      : {0} png files under {1}" -f $figures.Count, (Join-Path $AnalysisDir "figures"))
Write-Host ("    transcripts  : $LogDir")
Write-Host ("    summary      : $(Join-Path $OutDir 'reproduce.json')")
Write-Host "    nothing outside the output directory was written or deleted"
