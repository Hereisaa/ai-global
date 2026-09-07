# ai-global deploy script (native Windows / PowerShell).
#
# Same contract as setup/install.sh: copies this clone's global AI config into
# the paths the tools actually read. Everything deployed is a REAL FILE - no
# symlinks, no junctions - so a moved or deleted clone can never leave the
# machine with a dangling global config.
#
#   repo\governance   -> %USERPROFILE%\.ai-global\governance   (rules SSOT)
#   repo\manifest     -> %USERPROFILE%\.ai-global\manifest
#   repo\claude\*     -> %USERPROFILE%\.claude\*
#   repo\codex\*      -> %USERPROFILE%\.codex\*
#
# Usage: powershell -ExecutionPolicy Bypass -File setup\install.ps1 [-Mode install|check]
param([ValidateSet("install", "check")][string]$Mode = "install")
$ErrorActionPreference = "Stop"

$Repo   = Split-Path -Parent $PSScriptRoot
$H      = $env:USERPROFILE
$Global = Join-Path $H ".ai-global"
$State  = Join-Path $Global ".deploy-state.json"
$Trash  = Join-Path $H (".ai-trash\ai-global-deploy-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
$script:Fail = 0

# Commit this machine was last deployed from. Lets check tell "the repo moved
# on" (safe to update) apart from "someone edited the deployed copy" (review).
$PrevCommit = ""
if (Test-Path -LiteralPath $State) {
  try { $PrevCommit = (Get-Content -LiteralPath $State -Raw | ConvertFrom-Json).commit } catch { $PrevCommit = "" }
}

# Get-Item -Force also returns dangling links, which Test-Path reports as absent.
function Get-Existing($P) { Get-Item -LiteralPath $P -Force -ErrorAction SilentlyContinue }

# Raw byte compare instead of Get-FileHash: module autoloading is unreliable when
# PowerShell is launched from Git Bash, and these files are all small.
function Test-SameContent($A, $B) {
  $ia = Get-Item -LiteralPath $A
  $ib = Get-Item -LiteralPath $B
  if ($ia.Length -ne $ib.Length) { return $false }
  $ba = [System.IO.File]::ReadAllBytes($ia.FullName)
  $bb = [System.IO.File]::ReadAllBytes($ib.FullName)
  for ($i = 0; $i -lt $ba.Length; $i++) { if ($ba[$i] -ne $bb[$i]) { return $false } }
  return $true
}

function Move-ToTrash($P) {
  $item = Get-Existing $P
  if (-not $item) { return }
  if ($item.LinkType) {
    # A symlink/junction carries no data of its own: drop the link, keep whatever
    # it pointed at. Nothing recoverable is lost, so this needs no trash copy.
    if ($item.PSIsContainer) { [System.IO.Directory]::Delete($item.FullName) }
    else { [System.IO.File]::Delete($item.FullName) }
    Write-Host "UNLINK  $P (link left by an older install)"
    return
  }
  $label = $item.FullName
  if ($label.StartsWith($H, [StringComparison]::OrdinalIgnoreCase)) {
    $label = $label.Substring($H.Length).TrimStart('\')
  } else {
    $label = Split-Path $label -Leaf
  }
  $dest = Join-Path $Trash $label
  New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
  Move-Item -LiteralPath $item.FullName -Destination $dest
}

function Get-Status($Rel, $Dst) {
  $src  = Join-Path $Repo $Rel
  $item = Get-Existing $Dst
  if (-not $item) { return "MISSING" }
  # Nothing deployed is ever a link, so any link here is left over from an older
  # install - dangling or not. (Test-Path still reports dangling links as present.)
  if ($item.LinkType) { return "STALE" }
  if (-not [System.IO.File]::Exists($item.FullName)) { return "EDITED" }
  if (Test-SameContent $src $Dst) { return "OK" }
  if ($PrevCommit) {
    $prevBlob = & git -C $Repo rev-parse "$($PrevCommit):$Rel" 2>$null
    $dstBlob  = & git -C $Repo hash-object $Dst 2>$null
    if ($prevBlob -and $prevBlob -eq $dstBlob) { return "BEHIND" }
  }
  return "EDITED"
}

function Put($Rel, $Dst) {
  $src = Join-Path $Repo $Rel
  if (-not (Test-Path -LiteralPath $src -PathType Leaf)) { Write-Host "SKIP    $Rel missing in repo"; return }
  $st = Get-Status $Rel $Dst
  if ($Mode -eq "check") {
    switch ($st) {
      "OK"      { Write-Host "OK      $Dst" }
      "MISSING" { Write-Host "MISSING $Dst - not deployed yet";                                $script:Fail = 1 }
      "STALE"   { Write-Host "STALE   $Dst - dangling link left by an older install";          $script:Fail = 1 }
      "BEHIND"  { Write-Host "BEHIND  $Dst - repo moved on, run install to update";            $script:Fail = 1 }
      "EDITED"  { Write-Host "EDITED  $Dst - changed outside the repo, review before install"; $script:Fail = 1 }
    }
    return
  }
  if ($st -eq "OK") { return }
  if ($st -eq "EDITED") { Write-Host "WARN    $Dst differed from the repo; the old copy goes to trash" }
  Move-ToTrash $Dst
  New-Item -ItemType Directory -Force -Path (Split-Path $Dst -Parent) | Out-Null
  Copy-Item -LiteralPath $src -Destination $Dst -Force
  Write-Host "PUT     $Dst"
}

function PutDir($Rel, $Dst) {
  $src = Join-Path $Repo $Rel
  if (-not (Test-Path -LiteralPath $src -PathType Container)) { Write-Host "SKIP    $Rel missing in repo"; return }
  # A directory left as a junction by an older install must go first, otherwise
  # every copy below would be written straight back into the repo.
  if ($Mode -eq "install") {
    $d = Get-Existing $Dst
    if ($d -and $d.LinkType) { Move-ToTrash $Dst }
  }
  $srcRoot = (Resolve-Path -LiteralPath $src).Path
  $skip    = Join-Path $srcRoot "backups"
  foreach ($f in Get-ChildItem -LiteralPath $srcRoot -Recurse -File) {
    if ($f.Name -eq ".gitkeep") { continue }
    if ($f.FullName.StartsWith($skip, [StringComparison]::OrdinalIgnoreCase)) { continue }
    $sub = $f.FullName.Substring($srcRoot.Length).TrimStart('\').Replace('\', '/')
    Put "$Rel/$sub" (Join-Path $Dst $sub)
  }
  # Skip the extras scan when the destination is still a link: install already
  # unlinked it above, and in check mode every file under it is reported as
  # STALE/MISSING anyway. Enumerating a dangling one would just throw.
  $d = Get-Existing $Dst
  if (-not $d -or $d.LinkType) { return }
  if (-not [System.IO.Directory]::Exists($Dst)) { return }
  # files that no longer exist in the repo
  $dstRoot = (Resolve-Path -LiteralPath $Dst).Path
  foreach ($f in Get-ChildItem -LiteralPath $dstRoot -Recurse -File) {
    $sub = $f.FullName.Substring($dstRoot.Length).TrimStart('\')
    if (Test-Path -LiteralPath (Join-Path $srcRoot $sub)) { continue }
    if ($Mode -eq "check") { Write-Host "EXTRA   $($f.FullName) - no longer in repo"; $script:Fail = 1 }
    else { Move-ToTrash $f.FullName; Write-Host "DROP    $($f.FullName) -> trash" }
  }
}

Write-Host "repo:   $Repo"
Write-Host "target: $Global + $H\.claude + $H\.codex"
Write-Host ""

PutDir "governance"           "$Global\governance"
PutDir "manifest"             "$Global\manifest"
PutDir "claude/hooks"         "$H\.claude\hooks"
Put    "claude/CLAUDE.md"     "$H\.claude\CLAUDE.md"
Put    "claude/statusline.sh" "$H\.claude\statusline.sh"
Put    "codex/AGENTS.md"      "$H\.codex\AGENTS.md"

# Repo-owned skills/commands/agents are deployed item by item so third-party
# installs keep coexisting in the same parent directories.
Get-ChildItem -LiteralPath "$Repo\claude\skills" -Directory -ErrorAction SilentlyContinue |
  ForEach-Object { PutDir "claude/skills/$($_.Name)" "$H\.claude\skills\$($_.Name)" }
Get-ChildItem -LiteralPath "$Repo\claude\commands" -File -ErrorAction SilentlyContinue |
  Where-Object Name -ne ".gitkeep" |
  ForEach-Object { Put "claude/commands/$($_.Name)" "$H\.claude\commands\$($_.Name)" }
Get-ChildItem -LiteralPath "$Repo\claude\agents" -File -ErrorAction SilentlyContinue |
  Where-Object Name -ne ".gitkeep" |
  ForEach-Object { Put "claude/agents/$($_.Name)" "$H\.claude\agents\$($_.Name)" }

$HeadCommit = (& git -C $Repo rev-parse HEAD 2>$null)
if (-not $HeadCommit) { $HeadCommit = "unknown" }

if ($Mode -eq "check") {
  Write-Host ""
  if (-not $PrevCommit) { Write-Host "STATE   never deployed on this machine" }
  elseif ($PrevCommit -ne $HeadCommit) { Write-Host "STATE   deployed from $($PrevCommit.Substring(0,9)), repo HEAD is $($HeadCommit.Substring(0,9))" }
  else { Write-Host "STATE   deployed from $($PrevCommit.Substring(0,9)) (current)" }
  if ($script:Fail -eq 0) { Write-Host "global deployment is in sync"; exit 0 }
  Write-Host "out of sync - run: powershell -ExecutionPolicy Bypass -File $Repo\setup\install.ps1"
  exit 1
}

$Branch = (& git -C $Repo rev-parse --abbrev-ref HEAD 2>$null)
if (-not $Branch) { $Branch = "unknown" }
New-Item -ItemType Directory -Force -Path $Global | Out-Null
# Each element is parenthesised on purpose: inside an array literal PowerShell
# binds "," tighter than "+", so an unparenthesised concatenation would be split
# into separate elements and the joined JSON would come out with stray newlines.
$json = @(
  '{',
  ('  "source_repo": "' + $Repo.Replace('\', '\\') + '",'),
  ('  "commit": "' + $HeadCommit + '",'),
  ('  "branch": "' + $Branch + '",'),
  ('  "deployed_at": "' + (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") + '",'),
  '  "platform": "Windows"',
  '}'
) -join "`n"
[System.IO.File]::WriteAllText($State, $json + "`n", (New-Object System.Text.UTF8Encoding $false))
Write-Host "STATE   $State -> $($HeadCommit.Substring(0,9))"

# Remind after a pull. Deliberately does not auto-deploy, so a pull can never
# silently overwrite something that was edited on this machine.
$hookDir = Join-Path $Repo ".git\hooks"
if (Test-Path -LiteralPath $hookDir) {
  $hook = "#!/bin/sh`necho 'ai-global: pull done -> run setup/install.ps1 -Mode check'`n"
  [System.IO.File]::WriteAllText((Join-Path $hookDir "post-merge"), $hook, (New-Object System.Text.UTF8Encoding $false))
}

if (Test-Path -LiteralPath $Trash) {
  Write-Host ""
  Write-Host "NOTE: replaced items are in $Trash (confirm, then empty manually)"
}
Write-Host "deploy complete"
