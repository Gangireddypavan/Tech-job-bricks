# Runs notebooks/04_extract in batches until no posts are pending, then rebuilds the
# normalized skills table (05_skills). Stops at the first failed batch (for example when the
# Free Edition daily compute quota is hit); re-running picks up where it left off.
#
#   pwsh scripts/run_extraction.ps1 -BatchSize 1000

param(
    [int]$BatchSize = 1000,
    [int]$MaxBatches = 20,
    [string]$Endpoint = "databricks-gpt-oss-120b",
    [string]$DbProfile = "Brick",
    [string]$WarehouseId = "1248956e7aafdfec",
    [string]$Base = "/Workspace/Users/pavangangireddy53@gmail.com/hn_jobs",
    [string]$Log = (Join-Path $PSScriptRoot "..\logs\extraction.log")
)

New-Item -ItemType Directory -Force (Split-Path $Log) | Out-Null

function Write-Log($msg) {
    $line = "{0:u}  {1}" -f (Get-Date), $msg
    Add-Content -Path $Log -Value $line
    Write-Output $line
}

# Submit a one-time run, poll until it finishes, return state + the first task's notebook output.
function Invoke-Run($runName, $tasks) {
    $f = New-TemporaryFile
    @{ run_name = $runName; tasks = $tasks } | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 $f
    $submitted = databricks jobs submit --no-wait --json "@$f" --profile $DbProfile -o json | ConvertFrom-Json
    Remove-Item $f
    if (-not $submitted.run_id) { return [pscustomobject]@{ ok = $false; state = "SUBMIT_FAILED" } }

    do {
        Start-Sleep -Seconds 30
        $run = databricks jobs get-run $submitted.run_id --profile $DbProfile -o json | ConvertFrom-Json
        $life = $run.state.life_cycle_state
    } while ($life -notin @("TERMINATED", "SKIPPED", "INTERNAL_ERROR"))

    $out = databricks jobs get-run-output $run.tasks[0].run_id --profile $DbProfile -o json | ConvertFrom-Json
    [pscustomobject]@{
        ok     = $run.state.result_state -eq "SUCCESS"
        state  = "$life/$($run.state.result_state)"
        result = $out.notebook_output.result
        error  = "$($out.error) $($run.state.state_message)".Trim()
        url    = $run.run_page_url
    }
}

Write-Log "start: endpoint=$Endpoint batch_size=$BatchSize max_batches=$MaxBatches"
for ($i = 1; $i -le $MaxBatches; $i++) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $r = Invoke-Run "hn-extract-batch-$i" @(@{
        task_key = "extract"
        notebook_task = @{ notebook_path = "$Base/04_extract"; base_parameters = @{ batch_size = "$BatchSize"; endpoint = $Endpoint } }
    })
    $mins = [int]$sw.Elapsed.TotalMinutes
    if (-not $r.ok) {
        Write-Log "batch $i FAILED ($($r.state)) after $mins min: $($r.error) $($r.url)"
        exit 1
    }
    $s = $r.result | ConvertFrom-Json
    Write-Log ("batch {0}: rows={1} errors={2} llm={3}s total={4}min pending_after={5} gold_rows={6}" -f `
        $i, $s.batch_rows, $s.batch_errors, $s.llm_seconds, $mins, $s.pending_after, $s.gold_rows)
    if ($s.pending_after -eq 0 -or $s.batch_rows -eq 0) { break }
    if ($s.batch_errors -eq $s.batch_rows) {
        Write-Log "every row in batch $i errored; stopping so the same posts aren't retried forever"
        exit 1
    }
}

$r = Invoke-Run "hn-skills" @(@{
    task_key = "skills"
    notebook_task = @{ notebook_path = "$Base/05_skills"; warehouse_id = $WarehouseId }
})
Write-Log "skills rebuild: $($r.state) $($r.error)"
Write-Log "done"
