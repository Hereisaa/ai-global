<#
.SYNOPSIS
  Reclaim memory left behind by Claude Code sessions on Windows.

.DESCRIPTION
  Two scopes:
    -Scope session  Run from a Claude Code SessionEnd hook. Kills helper
                    processes (MCP servers, dev servers, emulators, headless
                    browsers) that descend from the ending session only.
    -Scope global   Run manually. Reports orphan candidates, large sessions
                    and VM usage. Lost ancestry cannot prove ownership, so
                    global scope never stops processes or virtual machines.

  Safety rules:
    * A `claude` main process is NEVER killed. Remote Control is a long-lived
      `claude` process that may legitimately have no living parent.
    * Any process whose own or ancestor command line contains
      "remote-control" is skipped, together with its whole subtree.
    * Parent liveness accounts for PID reuse: a "parent" created after its
      child is treated as dead.
#>
[CmdletBinding()]
param(
  [ValidateSet('session', 'global')] [string] $Scope = 'global',
  [int] $ClaudeMemoryWarnMB = 1536,
  [int] $ClaudeAgeWarnHours = 24,
  [int] $VmmemShutdownMB = 3072,
  [switch] $DryRun
)

$ErrorActionPreference = 'SilentlyContinue'
$logDir = Join-Path $HOME '.claude\logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$log = Join-Path $logDir 'cleanup.log'

function Write-Log([string] $msg) {
  $line = "{0} [{1}] {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Scope, $msg
  Add-Content -Path $log -Value $line -Encoding UTF8
}

# Candidate helper names; session ancestry must also prove ownership.
$helperNames = @('node', 'dart', 'emulator', 'qemu-system-x86_64', 'chrome', 'msedge', 'chromium', 'bun', 'python', 'pwsh', 'powershell', 'bash', 'sh')
# Browsers count only when running headless (interactive windows are the user's).
$headlessOnly = @('chrome', 'msedge', 'chromium')

$all = @{}
Get-CimInstance Win32_Process | ForEach-Object {
  $all[[int]$_.ProcessId] = [pscustomobject]@{
    Pid     = [int]$_.ProcessId
    Ppid    = [int]$_.ParentProcessId
    Name    = ($_.Name -replace '\.exe$', '')
    Cmd     = [string]$_.CommandLine
    Created = $_.CreationDate
    WS      = [long]$_.WorkingSetSize
  }
}

function Get-LiveParent($p) {
  $parent = $all[$p.Ppid]
  if ($null -eq $parent) { return $null }
  if ($parent.Created -and $p.Created -and $parent.Created -gt $p.Created) { return $null }  # PID reused
  return $parent
}

function Test-RemoteControlLineage($p) {
  $cur = $p; $guard = 0
  while ($cur -and $guard -lt 64) {
    if ($cur.Cmd -match 'remote-control') { return $true }
    $cur = Get-LiveParent $cur; $guard++
  }
  return $false
}

function Test-IsHelper($p) {
  if ($helperNames -notcontains $p.Name) { return $false }
  if ($headlessOnly -contains $p.Name -and $p.Cmd -notmatch '--headless') { return $false }
  return $true
}

function Stop-Tracked($p, [string] $reason) {
  $mb = [math]::Round($p.WS / 1MB)
  if ($DryRun) { Write-Log "DRYRUN kill $($p.Name) pid=$($p.Pid) ${mb}MB ($reason)"; return }
  Stop-Process -Id $p.Pid -Force
  Write-Log "killed $($p.Name) pid=$($p.Pid) ${mb}MB ($reason)"
}

function Get-Descendants([int] $rootPid) {
  $out = @(); $queue = New-Object System.Collections.Queue
  $queue.Enqueue($rootPid)
  while ($queue.Count -gt 0) {
    $cur = $queue.Dequeue()
    foreach ($p in $all.Values) {
      if ($p.Ppid -eq $cur -and $p.Pid -ne $rootPid -and (Get-LiveParent $p)) { $out += $p; $queue.Enqueue($p.Pid) }
    }
  }
  return $out
}

if ($Scope -eq 'session') {
  # Hook process -> parent is the ending claude session.
  $self = $all[$PID]
  $claude = Get-LiveParent $self
  if (-not $claude -or $claude.Name -ne 'claude') { Write-Log "session scope: parent is not claude, skip"; exit 0 }
  if (Test-RemoteControlLineage $claude) { Write-Log "session scope: remote-control session, skip"; exit 0 }
  $mine = @(Get-Descendants $PID | ForEach-Object { $_.Pid })
  foreach ($p in Get-Descendants $claude.Pid) {
    if ($p.Pid -eq $PID -or $mine -contains $p.Pid) { continue }
    if ($p.Name -eq 'claude') { continue }
    if (Test-RemoteControlLineage $p) { continue }
    if (Test-IsHelper $p) { Stop-Tracked $p "descendant of ending session $($claude.Pid)" }
  }
  exit 0
}

# ---- global scope ----
$killed = 0
foreach ($p in $all.Values) {
  if (-not (Test-IsHelper $p)) { continue }
  if (Get-LiveParent $p) { continue }             # parent alive -> not an orphan
  if (Test-RemoteControlLineage $p) { continue }
  Write-Log "candidate $($p.Name) pid=$($p.Pid): ownership unknown (report only)"
}

# Report long-lived or large claude sessions; never kill them.
$warn = @()
foreach ($p in $all.Values) {
  if ($p.Name -ne 'claude') { continue }
  $mb = [math]::Round($p.WS / 1MB)
  $age = 0
  if ($p.Created) { $age = [math]::Round(((Get-Date) - $p.Created).TotalHours, 1) }
  $rc = ''
  if ($p.Cmd -match 'remote-control') { $rc = ' remote-control' }
  if ($mb -ge $ClaudeMemoryWarnMB -or $age -ge $ClaudeAgeWarnHours) {
    $warn += "pid $($p.Pid): ${mb}MB, ${age}h$rc"
  }
}
if ($warn.Count -gt 0) {
  Write-Log ("claude sessions worth a look: " + ($warn -join '; '))
  try {
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
    $nodes = $xml.GetElementsByTagName('text')
    $nodes.Item(0).AppendChild($xml.CreateTextNode('Claude Code: long-lived sessions')) | Out-Null
    $nodes.Item(1).AppendChild($xml.CreateTextNode(($warn -join [Environment]::NewLine))) | Out-Null
    $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Claude Code cleanup').Show($toast)
  } catch { Write-Log "toast failed: $($_.Exception.Message)" }
}

# Global VM ownership cannot be attributed to an ending session.
$vmmemSum = 0
foreach ($p in $all.Values) { if ($p.Name -match '^vmmem') { $vmmemSum += $p.WS } }
$vmmemMB = [math]::Round($vmmemSum / 1MB)
if ($vmmemMB -ge $VmmemShutdownMB) {
  try {
    $containers = @(& docker ps -q 2>$null)
    if ($LASTEXITCODE -ne 0) { throw 'docker query failed' }
    $running = @(& wsl --list --running --quiet 2>$null)
    if ($LASTEXITCODE -ne 0) { throw 'wsl query failed' }
    $runningCount = @($running | ForEach-Object { ($_ -replace "`0", '').Trim() } | Where-Object { $_ }).Count
    Write-Log "vmmem ${vmmemMB}MB containers=$($containers.Count) runningDistros=$runningCount (report only)"
  } catch {
    Write-Log "vmmem ${vmmemMB}MB usage unknown: VM query failed (report only)"
  }
}

Write-Log "done: killed=$killed warned=$($warn.Count) vmmem=${vmmemMB}MB"
