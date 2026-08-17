# ai-global deploy script (native Windows).
# Junctions for directories (no privilege needed); symlinks for files, falling
# back to copy when symlinks are unavailable (enable Developer Mode to avoid it).
# Never deletes: pre-existing items are moved to %USERPROFILE%\Developer\temp\trash\.
$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $PSScriptRoot
$H = $env:USERPROFILE
$Trash = Join-Path $H ("Developer\temp\trash\ai-global-install-" + (Get-Date -Format "yyyyMMdd-HHmmss"))

function Deploy($Src, $Dst) {
  if (-not (Test-Path $Src)) { Write-Host "SKIP  $Src missing in repo"; return }
  $isDir = (Get-Item $Src).PSIsContainer
  $existing = Get-Item $Dst -ErrorAction SilentlyContinue
  if ($existing -and $existing.LinkType -and ($existing.Target -contains $Src)) { return }
  if (Test-Path $Dst) {
    New-Item -ItemType Directory -Force -Path $Trash | Out-Null
    Move-Item $Dst (Join-Path $Trash (Split-Path $Dst -Leaf))
    Write-Host "MOVED $Dst -> trash"
  }
  New-Item -ItemType Directory -Force -Path (Split-Path $Dst -Parent) | Out-Null
  if ($isDir) {
    New-Item -ItemType Junction -Path $Dst -Target $Src | Out-Null
    Write-Host "JUNC  $Dst -> $Src"
  } else {
    try {
      New-Item -ItemType SymbolicLink -Path $Dst -Target $Src | Out-Null
      Write-Host "LINK  $Dst -> $Src"
    } catch {
      Copy-Item $Src $Dst
      Write-Host "COPY  $Dst (symlink unavailable; enable Developer Mode, else re-run to resync after edits)"
    }
  }
}

Deploy "$Repo\governance"           "$H\Developer\agent-governance"
Deploy "$Repo\claude\CLAUDE.md"     "$H\.claude\CLAUDE.md"
Deploy "$Repo\claude\statusline.sh" "$H\.claude\statusline.sh"
Deploy "$Repo\claude\hooks"         "$H\.claude\hooks"
Deploy "$Repo\codex\AGENTS.md"      "$H\.codex\AGENTS.md"

Get-ChildItem -Directory "$Repo\claude\skills" | ForEach-Object { Deploy $_.FullName "$H\.claude\skills\$($_.Name)" }
Get-ChildItem -File "$Repo\claude\commands" | Where-Object Name -ne ".gitkeep" | ForEach-Object { Deploy $_.FullName "$H\.claude\commands\$($_.Name)" }
Get-ChildItem "$Repo\claude\agents" -ErrorAction SilentlyContinue | Where-Object Name -ne ".gitkeep" | ForEach-Object { Deploy $_.FullName "$H\.claude\agents\$($_.Name)" }

if (Test-Path $Trash) { Write-Host "NOTE: replaced items moved to $Trash (confirm, then empty manually)" }
Write-Host "deploy complete"
