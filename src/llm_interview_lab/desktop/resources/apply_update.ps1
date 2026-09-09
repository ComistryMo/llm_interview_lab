param([string]$AppPath, [string]$NextPath, [string]$PreviousPath,
      [int]$AppPid, [string]$ReceiptPath, [string]$EntryPoint)
$ErrorActionPreference = 'Stop'
$UpdateDirectory = [IO.Path]::GetDirectoryName($ReceiptPath)
$StatusPath = Join-Path $UpdateDirectory 'status'
$ReadyPath = Join-Path $UpdateDirectory 'ready'
$FailedPath = Join-Path $UpdateDirectory 'failed'
$MovedOldApp = $false
$StartedApp = $null
try {
    for ($attempt = 0; $attempt -lt 120; $attempt++) {
        if (-not (Get-Process -Id $AppPid -ErrorAction SilentlyContinue)) { break }
        Start-Sleep -Milliseconds 500
    }
    if (Get-Process -Id $AppPid -ErrorAction SilentlyContinue) { throw 'WAIT_EXIT' }
    Move-Item -LiteralPath $AppPath -Destination $PreviousPath
    $MovedOldApp = $true
    Move-Item -LiteralPath $NextPath -Destination $AppPath
    $env:LLM_LAB_UPDATE_HANDOFF = $ReceiptPath
    $StartedApp = Start-Process -FilePath (Join-Path $AppPath $EntryPoint) -WorkingDirectory $AppPath -PassThru
    for ($attempt = 0; $attempt -lt 180; $attempt++) {
        if (Test-Path -LiteralPath $ReadyPath) {
            [IO.File]::WriteAllText($StatusPath, 'installed')
            exit 0
        }
        $StartedApp.Refresh()
        if ($StartedApp.HasExited) { throw 'NEW_APP_EXITED' }
        Start-Sleep -Milliseconds 500
    }
    # Never kill an unresponsive user process. Keep both versions for recovery.
    [IO.File]::WriteAllText($StatusPath, 'unconfirmed')
    exit 2
} catch {
    if ($MovedOldApp) {
        if (Test-Path -LiteralPath $AppPath) { Move-Item -LiteralPath $AppPath -Destination $FailedPath }
        Move-Item -LiteralPath $PreviousPath -Destination $AppPath
        [Environment]::SetEnvironmentVariable('LLM_LAB_UPDATE_HANDOFF', $null, 'Process')
        [IO.File]::WriteAllText($StatusPath, 'rolled_back')
        Start-Process -FilePath (Join-Path $AppPath $EntryPoint) -WorkingDirectory $AppPath
    } else {
        [IO.File]::WriteAllText($StatusPath, 'install_failed')
        if (-not (Get-Process -Id $AppPid -ErrorAction SilentlyContinue)) {
            Start-Process -FilePath (Join-Path $AppPath $EntryPoint) -WorkingDirectory $AppPath
        }
    }
    exit 1
}
