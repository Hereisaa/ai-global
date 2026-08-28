<#
.SYNOPSIS
  Register (or remove) the Windows scheduled task that runs
  ~/.claude/hooks/cleanup-orphans.ps1 -Scope global every N hours and at logon.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File setup\install-cleanup-task.ps1
  powershell -ExecutionPolicy Bypass -File setup\install-cleanup-task.ps1 -IntervalHours 4
  powershell -ExecutionPolicy Bypass -File setup\install-cleanup-task.ps1 -Uninstall
#>
param(
  [int] $IntervalHours = 2,
  [switch] $Uninstall
)
$taskName = 'ClaudeCodeOrphanCleanup'
$script = Join-Path $HOME '.claude\hooks\cleanup-orphans.ps1'

if ($Uninstall) {
  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Host "Removed scheduled task $taskName"
  exit 0
}
if (-not (Test-Path $script)) { Write-Error "Script not found: $script (run setup\install.ps1 first)"; exit 1 }

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
  -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`" -Scope global"
$triggers = @(
  (New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Hours $IntervalHours)),
  (New-ScheduledTaskTrigger -AtLogOn -User ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name))
)
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
  -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $triggers -Settings $settings -Force -ErrorAction Stop | Out-Null
Write-Host "Registered $taskName : every ${IntervalHours}h + at logon -> $script"
Write-Host "Log: $HOME\.claude\logs\cleanup.log"
