# ai-global deploy script (native Windows / PowerShell).
#
# Same contract as setup/install.sh: copies this clone's global AI config into
# the paths the tools actually read. Everything deployed is a REAL FILE - no
# symlinks, no junctions - so a moved or deleted clone can never leave the
# machine with a dangling global config.
#
#   repo\governance   -> %USERPROFILE%\.ai-global\governance   (rules SSOT)
#   repo\claude\*     -> %USERPROFILE%\.claude\*
#   repo\codex\*      -> %USERPROFILE%\.codex\*
#
# Usage: powershell -ExecutionPolicy Bypass -File setup\install.ps1 [-Mode install|check]
param([ValidateSet("install", "check")][string]$Mode = "install", [string]$TargetHome = $env:USERPROFILE)
$ErrorActionPreference = "Stop"

$Repo   = Split-Path -Parent $PSScriptRoot
$H      = [System.IO.Path]::GetFullPath($TargetHome)
$Global = Join-Path $H ".ai-global"
$State  = Join-Path $Global ".deploy-state.json"
$Trash  = Join-Path $H (".ai-trash\ai-global-deploy-" + (Get-Date -Format "yyyyMMdd-HHmmss") + "-" + [guid]::NewGuid().ToString('N'))
$script:Fail = 0

# State from the previous deploy on this machine (~/.ai-global/.deploy-state.json):
#   files    blob hash of every file as deployed. A deployed file that still
#            matches its recorded hash was not touched since -> BEHIND (safe to
#            update); anything else -> EDITED (needs a human). Hashes rather
#            than a commit, so deploying from a dirty worktree stays accurate.
#   managed  repo-relative paths of the item-level deploys (skills, commands,
#            agents). An item the repo no longer has must be removed, or the
#            tool keeps loading a skill that no longer exists upstream.
#   commit   informational only.
# Parsed with regex rather than ConvertFrom-Json: cmdlet autoloading is
# unreliable when PowerShell is launched from Git Bash.
$PrevCommit  = ""
$PrevManaged = @()
$script:StateRaw = ""
if (Test-Path -LiteralPath $State) {
  $script:StateRaw = [System.IO.File]::ReadAllText($State)
  $m = [regex]::Match($script:StateRaw, '"commit"\s*:\s*"([^"]*)"')
  if ($m.Success) { $PrevCommit = $m.Groups[1].Value }
  # Scope to the managed array: the files map below also has "claude/..." keys.
  $mm = [regex]::Match($script:StateRaw, '"managed"\s*:\s*\[(.*?)\]', 'Singleline')
  if ($mm.Success) {
    $PrevManaged = @([regex]::Matches($mm.Groups[1].Value, '"(claude/[^"]*)"') | ForEach-Object { $_.Groups[1].Value })
  }
}
$script:Managed = New-Object System.Collections.Generic.List[string]
$script:Files   = New-Object System.Collections.Generic.List[string]

function Get-PrevHash($Rel) {
  if (-not $script:StateRaw) { return "" }
  $m = [regex]::Match($script:StateRaw, '"' + [regex]::Escape($Rel) + '"\s*:\s*"([0-9a-f]+)"')
  if ($m.Success) { return $m.Groups[1].Value }
  return ""
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
  $label = $item.FullName
  if ($label.StartsWith($H, [StringComparison]::OrdinalIgnoreCase)) {
    $label = $label.Substring($H.Length).TrimStart('\')
  } else {
    $label = Split-Path $label -Leaf
  }
  $dest = Join-Path $Trash $label
  if (-not $item.FullName.StartsWith($H.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw "Trash source is outside the selected home"
  }
  New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
  if (Get-Existing $dest) { throw "Trash destination already exists" }
  if ($item.PSIsContainer) { [System.IO.Directory]::Move($item.FullName, $dest) }
  else { [System.IO.File]::Move($item.FullName, $dest) }
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
  $prev = Get-PrevHash $Rel
  if ($prev) {
    $dstBlob = & git -C $Repo hash-object $Dst 2>$null
    if ($prev -eq $dstBlob) { return "BEHIND" }
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
  # Record what is deployed after this run, whether or not we had to copy.
  $script:Files.Add($Rel + "|" + (& git -C $Repo hash-object $src))
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
  if ($Mode -eq "install") {
    $d = Get-Existing $Dst
    # A directory left as a junction by an older install must go first, otherwise
    # every copy below would be written straight back into the repo.
    if ($d -and $d.LinkType) { Move-ToTrash $Dst }
    elseif ($d -and -not $d.PSIsContainer) {
      Write-Host "WARN    $Dst is a file where a directory belongs; the old copy goes to trash"
      Move-ToTrash $Dst
    }
  }
  $srcRoot = (Resolve-Path -LiteralPath $src).Path
  foreach ($f in Get-ChildItem -LiteralPath $srcRoot -Recurse -File) {
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

# ~/.ai-global is owned by this script outright, so anything at its top level
# that this version does not deploy is a leftover from an older layout.
if ([System.IO.Directory]::Exists($Global)) {
  foreach ($e in Get-ChildItem -LiteralPath $Global -Force) {
    if ($e.Name -in @("governance", ".deploy-state.json")) { continue }
    if ($Mode -eq "check") { Write-Host "EXTRA   $($e.FullName) - no longer deployed here"; $script:Fail = 1 }
    else { Move-ToTrash $e.FullName; Write-Host "DROP    $($e.FullName) -> trash" }
  }
}

PutDir "claude/hooks"         "$H\.claude\hooks"
Put    "claude/CLAUDE.md"     "$H\.claude\CLAUDE.md"
Put    "claude/statusline.sh" "$H\.claude\statusline.sh"
Put    "codex/AGENTS.md"      "$H\.codex\AGENTS.md"

# Repo-owned skills/commands/agents are deployed item by item so third-party
# installs keep coexisting in the same parent directories.
Get-ChildItem -LiteralPath "$Repo\claude\skills" -Directory -ErrorAction SilentlyContinue |
  ForEach-Object {
    if (Test-Path -LiteralPath "$H\.claude\ai-global-disabled\skills\$($_.Name)") {
      Write-Host "DISABLED claude/skills/$($_.Name) - preserving local choice"
      PutDir "claude/skills/$($_.Name)" "$H\.claude\ai-global-disabled\skills\$($_.Name)"
    } else { PutDir "claude/skills/$($_.Name)" "$H\.claude\skills\$($_.Name)" }
    $script:Managed.Add("claude/skills/$($_.Name)")
  }
Get-ChildItem -LiteralPath "$Repo\claude\commands" -File -ErrorAction SilentlyContinue |
  Where-Object Name -ne ".gitkeep" |
  ForEach-Object {
    if (Test-Path -LiteralPath "$H\.claude\ai-global-disabled\commands\$($_.Name)") {
      Write-Host "DISABLED claude/commands/$($_.Name) - preserving local choice"
      Put "claude/commands/$($_.Name)" "$H\.claude\ai-global-disabled\commands\$($_.Name)"
    } else { Put "claude/commands/$($_.Name)" "$H\.claude\commands\$($_.Name)" }
    $script:Managed.Add("claude/commands/$($_.Name)")
  }
Get-ChildItem -LiteralPath "$Repo\claude\agents" -File -ErrorAction SilentlyContinue |
  Where-Object Name -ne ".gitkeep" |
  ForEach-Object { Put "claude/agents/$($_.Name)" "$H\.claude\agents\$($_.Name)"; $script:Managed.Add("claude/agents/$($_.Name)") }

# Items deployed last time that the repo no longer has (a renamed or removed
# skill, command or agent).
foreach ($rel in $PrevManaged) {
  if (-not $rel -or $script:Managed.Contains($rel)) { continue }
  $dst = Join-Path $H (".claude\" + $rel.Substring("claude/".Length).Replace('/', '\'))
  if (-not (Get-Existing $dst)) { continue }
  if ($Mode -eq "check") { Write-Host "EXTRA   $dst - no longer in repo"; $script:Fail = 1 }
  else { Move-ToTrash $dst; Write-Host "DROP    $dst -> trash" }
}

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
  '  "platform": "Windows",',
  '  "managed": [',
  (($script:Managed | ForEach-Object { '    "' + $_ + '"' }) -join ",`n"),
  '  ],',
  '  "files": {',
  (($script:Files | ForEach-Object { $p = $_.Split('|', 2); '    "' + $p[0] + '": "' + $p[1] + '"' }) -join ",`n"),
  '  }',
  '}'
) -join "`n"
[System.IO.File]::WriteAllText($State, $json + "`n", (New-Object System.Text.UTF8Encoding $false))
Write-Host "STATE   $State -> $($HeadCommit.Substring(0,9))"

# Remind after a pull. Deliberately does not auto-deploy, so a pull can never
# silently overwrite something that was edited on this machine. post-merge
# covers plain/ff pulls, post-rewrite covers `pull --rebase`.
$hookDir = Join-Path $Repo ".git\hooks"
if (Test-Path -LiteralPath $hookDir) {
  $utf8 = New-Object System.Text.UTF8Encoding $false
  $msg  = "ai-global: pull done -> run setup/install.ps1 -Mode check (or /ai-global in Claude Code)"
  if (-not (Get-Existing (Join-Path $hookDir "post-merge"))) {
    [System.IO.File]::WriteAllText((Join-Path $hookDir "post-merge"), "#!/bin/sh`necho '$msg'`n", $utf8)
  }
  if (-not (Get-Existing (Join-Path $hookDir "post-rewrite"))) {
    [System.IO.File]::WriteAllText((Join-Path $hookDir "post-rewrite"), "#!/bin/sh`n[ `"`$1`" = rebase ] && echo '$msg'`nexit 0`n", $utf8)
  }
}

if (Test-Path -LiteralPath $Trash) {
  Write-Host ""
  Write-Host "NOTE: replaced items are in $Trash (confirm, then empty manually)"
}
Write-Host "deploy complete"
