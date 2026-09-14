#!/bin/bash
# Reclaim memory left behind by Claude Code sessions on macOS.
# macOS counterpart of cleanup-orphans.ps1; same two scopes, same log file.
#
#   --scope session   Run from a SessionEnd hook. Kills helper processes
#                     (MCP servers, dev servers, headless browsers) that
#                     descend from the ending session only.
#   --scope global    Report orphan candidates, large sessions and VM usage.
#                     Lost ancestry cannot prove ownership; never stop them.
#
# Safety rules (mirror the Windows script):
#   * A `claude` main process is NEVER killed. Remote Control is a long-lived
#     `claude` process that may legitimately have no living parent.
#   * Any process whose own or ancestor command line contains "remote-control"
#     is skipped, together with its whole subtree.
#   * Parent liveness accounts for PID reuse: a "parent" younger than its child
#     is treated as dead.
#
# macOS-specific rules (no Windows equivalent — these exist because orphaned
# processes here are reparented to launchd instead of losing their parent):
#   * ppid==1 is the orphan signal, so a launchd-managed PID (`launchctl list`)
#     is never a candidate — that is a service the user registered on purpose.
#   * Only processes owned by the invoking user are ever considered.
#   * Extra regexes in ~/.claude/cleanup-protect.txt are skipped.


set -u

SCOPE=global
DRY_RUN=0
CLAUDE_MEM_WARN_MB=1536
CLAUDE_AGE_WARN_H=24
VM_SHUTDOWN_MB=3072

while [ $# -gt 0 ]; do
  case "$1" in
    --scope) SCOPE="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --claude-mem-warn-mb) CLAUDE_MEM_WARN_MB="$2"; shift 2 ;;
    --claude-age-warn-h) CLAUDE_AGE_WARN_H="$2"; shift 2 ;;
    --vm-shutdown-mb) VM_SHUTDOWN_MB="$2"; shift 2 ;;
    *) shift ;;
  esac
done
case "$SCOPE" in session|global) ;; *) echo "unknown scope: $SCOPE" >&2; exit 2 ;; esac

LOG_DIR="$HOME/.claude/logs"
LOG="$LOG_DIR/cleanup.log"
PROTECT_FILE="$HOME/.claude/cleanup-protect.txt"
mkdir -p "$LOG_DIR"

log() { printf '%s [%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$SCOPE" "$1" >>"$LOG"; }

# SessionEnd delivers JSON on stdin; drain it so the hook never blocks on a pipe.
if [ "$SCOPE" = session ] && [ ! -t 0 ]; then cat >/dev/null 2>&1; fi

me=$$
user=$(id -un)

# Three ps passes joined by PID in awk: comm and args both contain spaces, so
# they cannot share a line with the numeric columns.
snapshot() {
  ps -U "$user" -o pid=,ppid=,etime=,rss= 2>/dev/null |
    awk '{print "P", $1, $2, $3, $4}'
  ps -U "$user" -o pid=,comm= 2>/dev/null |
    awk '{pid=$1; $1=""; sub(/^ +/,""); print "C", pid, $0}'
  ps -U "$user" -o pid=,args= 2>/dev/null |
    awk '{pid=$1; $1=""; sub(/^ +/,""); print "A", pid, $0}'
  launchctl list 2>/dev/null | awk '$1 ~ /^[0-9]+$/ {print "L", $1}'
  [ -f "$PROTECT_FILE" ] && grep -v '^[[:space:]]*#' "$PROTECT_FILE" | grep -v '^[[:space:]]*$' |
    awk '{print "R", $0}'
  return 0
}

DECISIONS=$(snapshot | awk \
  -v scope="$SCOPE" -v self="$me" \
  -v mem_warn="$CLAUDE_MEM_WARN_MB" -v age_warn="$CLAUDE_AGE_WARN_H" '
function etime2sec(e,   d, t, n, a, x) {
  d = 0; t = e
  if (index(e, "-") > 0) { split(e, x, "-"); d = x[1] + 0; t = x[2] }
  n = split(t, a, ":")
  if (n == 3) return d * 86400 + a[1] * 3600 + a[2] * 60 + a[3]
  if (n == 2) return d * 86400 + a[1] * 60 + a[2]
  return d * 86400 + a[1]
}
function base(p,   n, a) { n = split(p, a, "/"); return a[n] }
# 0 when the parent is gone or younger than the child (PID reuse).
function live_parent(p,   pp) {
  pp = PPID[p]
  if (pp == "" || pp == 0) return 0
  if (!(pp in PPID)) return 0
  if (AGE[pp] < AGE[p]) return 0
  return pp
}
function rc_lineage(p,   cur, guard) {
  cur = p; guard = 0
  while (cur != 0 && guard < 64) {
    if (ARGS[cur] ~ /remote-control/) return 1
    cur = live_parent(cur); guard++
  }
  return 0
}
function protected(p,   i) {
  if (p in LAUNCHD) return 1
  for (i = 1; i <= nprot; i++) if (ARGS[p] ~ PROT[i]) return 1
  return 0
}
function norm(c) { c = tolower(c); sub(/\.exe$/, "", c); return c }
# comm and argv[0] disagree often enough to matter: system python3 reports comm
# "Python", node dev servers rewrite argv to their own name.
function helper_name(p,   c1, c2, a) {
  c1 = norm(base(COMM[p]))
  split(ARGS[p], a, " "); c2 = norm(base(a[1]))
  if (c1 in HELPER) return c1
  if (c2 in HELPER) return c2
  if (c1 ~ /^python[0-9.]*$/ || c2 ~ /^python[0-9.]*$/) return "python"
  if (c1 ~ /^node[0-9.]*$/ || c2 ~ /^node[0-9.]*$/) return "node"
  return ""
}
function is_helper(p,   c) {
  c = helper_name(p)
  if (c == "") return 0
  if ((c in HEADLESS_ONLY) && ARGS[p] !~ /--headless/) return 0
  return 1
}
function descends_from(p, root,   cur, guard) {
  cur = live_parent(p); guard = 0
  while (cur != 0 && guard < 64) {
    if (cur == root) return 1
    cur = live_parent(cur); guard++
  }
  return 0
}
BEGIN {
  split("node deno bun python python2 python3 ruby php java dart esbuild " \
        "qemu-system-aarch64 qemu-system-x86_64 emulator docker-agent " \
        "chrome chromium headless_shell", h, " ")
  for (i in h) HELPER[h[i]] = 1
  split("chrome chromium", ho, " ")
  for (i in ho) HEADLESS_ONLY[ho[i]] = 1
  nprot = 0
}
$1 == "P" { PPID[$2] = $3; AGE[$2] = etime2sec($4); RSS[$2] = $5; next }
$1 == "C" { pid = $2; $1 = ""; $2 = ""; sub(/^ +/, ""); COMM[pid] = $0; next }
$1 == "A" { pid = $2; $1 = ""; $2 = ""; sub(/^ +/, ""); ARGS[pid] = $0; next }
$1 == "L" { LAUNCHD[$2] = 1; next }
$1 == "R" { $1 = ""; sub(/^ +/, ""); PROT[++nprot] = $0; next }
END {
  if (scope == "session") {
    # Walk up from the hook process to the claude session that is ending.
    cur = self; claude = 0; guard = 0
    while (cur != 0 && guard < 64) {
      if (base(COMM[cur]) == "claude") { claude = cur; break }
      cur = live_parent(cur); guard++
    }
    if (claude == 0) { print "SKIP no claude ancestor"; exit }
    if (rc_lineage(claude)) { print "SKIP remote-control session " claude; exit }
    for (p in PPID) {
      if (p == self || p == claude) continue
      if (base(COMM[p]) == "claude") continue
      if (descends_from(p, self)) continue
      if (!descends_from(p, claude)) continue
      if (protected(p) || rc_lineage(p)) continue
      if (!is_helper(p)) continue
      print "KILL", p, RSS[p], helper_name(p), "descendant of ending session " claude
    }
    exit
  }

  for (p in PPID) {
    if (base(COMM[p]) == "claude") continue
    if (live_parent(p) != 0) continue          # parent alive -> not an orphan
    if (p == self || descends_from(p, self)) continue
    if (protected(p)) continue
    if (!is_helper(p)) continue
    if (rc_lineage(p)) continue
    print "REPORT", p, RSS[p], helper_name(p), "ownership unknown (parent gone)"
  }

  for (p in PPID) {
    if (base(COMM[p]) != "claude") continue
    mb = int(RSS[p] / 1024 + 0.5)
    hrs = int(AGE[p] / 360 + 0.5) / 10
    rc = (ARGS[p] ~ /remote-control/) ? " remote-control" : ""
    if (mb >= mem_warn || hrs >= age_warn) print "WARN", p, mb, hrs, rc
  }

  vm = 0
  for (p in PPID)
    if (ARGS[p] ~ /Virtualization\.VirtualMachine|qemu-system/) vm += RSS[p]
  print "VM", int(vm / 1024 + 0.5)
}
')

killed=0
warns=""
vm_mb=0

while IFS= read -r line; do
  [ -n "$line" ] || continue
  case "$line" in
    SKIP*) log "${line#SKIP }"; exit 0 ;;
    KILL*)
      set -- $line
      pid=$2; rss_kb=$3; name=$4
      shift 4
      reason="$*"
      mb=$(( (rss_kb + 512) / 1024 ))
      if [ "$DRY_RUN" = 1 ]; then
        log "DRYRUN kill $name pid=$pid ${mb}MB ($reason)"
      else
        kill -TERM "$pid" 2>/dev/null && log "killed $name pid=$pid ${mb}MB ($reason)"
        killed=$((killed + 1))
      fi
      ;;
    REPORT*) log "${line#REPORT } (report only)" ;;
    WARN*)
      set -- $line
      warns="${warns}${warns:+; }pid $2: $3MB, $4h${5:+ $5}"
      ;;
    VM*) vm_mb=${line#VM } ;;
  esac
done <<EOF
$DECISIONS
EOF

[ "$SCOPE" = session ] && { log "done: killed=$killed"; exit 0; }

if [ -n "$warns" ]; then
  log "claude sessions worth a look: $warns"
  osascript -e "display notification \"$warns\" with title \"Claude Code: long-lived sessions\"" 2>/dev/null
fi

# Global VM ownership cannot be attributed to an ending session.
if [ "${vm_mb:-0}" -ge "$VM_SHUTDOWN_MB" ]; then
  if containers=$(docker ps -q 2>/dev/null); then
    count=$(printf '%s' "$containers" | grep -c . || true)
    log "VM ${vm_mb}MB containers=$count (report only; other VM work may exist)"
  else
    log "VM ${vm_mb}MB usage unknown: docker query failed (report only)"
  fi
fi

# Docker Desktop duplicating an active non-Desktop context is pure overhead.
if pgrep -qx "com.docker.backend" 2>/dev/null; then
  ctx=$(docker context show 2>/dev/null)
  case "$ctx" in
    desktop-linux|"") ;;
    *) log "Docker Desktop running while active context is '$ctx' — quit Docker Desktop to reclaim ~600MB" ;;
  esac
fi

warn_n=$(printf '%s' "$warns" | tr ';' '\n' | grep -c 'pid ' || true)
log "done: killed=$killed warned=$warn_n vm=${vm_mb}MB"
