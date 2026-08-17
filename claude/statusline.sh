#!/usr/bin/env bash
# Claude Code status line (bash port of the PowerShell version)
# Shows: (repo·worktree) (git branch) [model], context usage, 5h quota, 7d quota, session tokens

input=$(cat)

# --- Parse JSON (missing/null -> empty string) -----------------------------
# One field per line, not @tsv: tab is an IFS whitespace char, so `read` would
# collapse consecutive tabs and shift every field left whenever one is missing.
# Built with a read loop rather than readarray/mapfile — macOS ships bash 3.2.
fields=()
while IFS= read -r line; do fields+=("$line"); done < <(
  printf '%s' "$input" | jq -r '
    [ (.workspace.current_dir // .cwd // "")
    , (.model.display_name // "")
    , (.context_window.used_percentage // "")
    , (.rate_limits.five_hour.used_percentage // "")
    , (.rate_limits.five_hour.resets_at // "")
    , (.rate_limits.seven_day.used_percentage // "")
    , (.rate_limits.seven_day.resets_at // "")
    , (.context_window.total_input_tokens // "")
    , (.context_window.total_output_tokens // "")
    ] | .[]' 2>/dev/null | tr -d '\r'
)
cwd=${fields[0]-}  model=${fields[1]-}  ctx=${fields[2]-}
fh=${fields[3]-}   fhr=${fields[4]-}    sd=${fields[5]-}  sdr=${fields[6]-}
tin=${fields[7]-}  tout=${fields[8]-}
[ -z "$cwd" ] && cwd="$PWD"

# --- Git branch ------------------------------------------------------------
gitBranch=""
if [ -n "$cwd" ] && [ -d "$cwd" ]; then
  gitBranch=$(git -C "$cwd" --no-optional-locks branch --show-current 2>/dev/null)
fi

# --- Workspace label -------------------------------------------------------
# Absolute paths are too long once worktrees are involved and push the branch
# and quota fields off screen. Show "repo" for the main checkout and
# "repo·worktree" for a linked worktree, so parallel sessions are tellable apart.
workspace_label() {
  local top common main_top repo wt
  top=$(git -C "$cwd" --no-optional-locks rev-parse --show-toplevel 2>/dev/null)
  if [ -z "$top" ]; then
    printf '%s' "${cwd/#$HOME/~}"
    return
  fi
  common=$(git -C "$cwd" --no-optional-locks rev-parse --path-format=absolute --git-common-dir 2>/dev/null)
  if [ -z "$common" ]; then
    printf '%s' "$(basename "$top")"
    return
  fi
  main_top=$(dirname "$common")
  repo=$(basename "$main_top")
  if [ "$top" = "$main_top" ]; then
    printf '%s' "$repo"
  else
    wt=$(basename "$top")
    wt=${wt#"$repo"-}   # digrit-mobile-optimization-x -> mobile-optimization-x
    printf '%s·%s' "$repo" "$wt"
  fi
}

# --- Helpers ---------------------------------------------------------------
ansi() { printf '\033[%sm%s\033[0m' "$1" "$2"; }

rnd() { # round a (possibly float) number to nearest integer; "" -> ""
  [ -z "$1" ] && { printf ''; return; }
  case "$1" in
    *[!0-9.+-]*) printf '' ;;
    *) LC_NUMERIC=C awk -v n="$1" 'BEGIN{printf "%.0f", n}' ;;
  esac
}

make_bar() { # $1=pct -> 8-cell █/░ bar
  local pct=$1 width=8 filled empty i b=""
  filled=$(( pct * width / 100 ))
  (( filled < 0 )) && filled=0
  (( filled > width )) && filled=width
  empty=$(( width - filled ))
  for ((i=0;i<filled;i++)); do b+="█"; done
  for ((i=0;i<empty;i++)); do b+="░"; done
  printf '%s' "$b"
}

time_left() { # $1=reset epoch seconds -> (Hh Mm) / (Mm) / ""
  local resets=$1 now diff h m
  [ -z "$resets" ] && { printf ''; return; }
  case "$resets" in
    *[!0-9.]*) printf ''; return ;;
  esac
  resets=${resets%.*}
  now=$(date +%s)
  diff=$(( resets - now ))
  (( diff <= 0 )) && { printf ''; return; }
  h=$(( diff / 3600 ))
  m=$(( (diff % 3600) / 60 ))
  if (( h > 0 )); then printf '(%dh%dm)' "$h" "$m"; else printf '(%dm)' "$m"; fi
}

qcolor() { # quota %: <=50 green, <=80 yellow, else red
  local p=$1
  if   (( p <= 50 )); then printf '32'
  elif (( p <= 80 )); then printf '33'
  else                     printf '31'
  fi
}

fmt_tokens() {
  local n=$1
  [ -z "$n" ] && n=0
  if   (( n >= 1000000 )); then LC_NUMERIC=C awk -v n="$n" 'BEGIN{printf "%.1fM", n/1000000}'
  elif (( n >= 1000 ));    then LC_NUMERIC=C awk -v n="$n" 'BEGIN{printf "%.1fk", n/1000}'
  else printf '%s' "$n"
  fi
}

# --- Assemble --------------------------------------------------------------
parts=$(ansi 34 "($(workspace_label))")

[ -n "$gitBranch" ] && parts+=" $(ansi 32 "($gitBranch)")"
[ -n "$model" ]     && parts+=" $(ansi 35 "[$model]")"

# Context window
if [ -n "$ctx" ]; then
  pct=$(rnd "$ctx")
  if [ -n "$pct" ]; then
    bar=$(make_bar "$pct")
    parts+=" $(ansi 36 "Ctx:")$(ansi 0 "${bar}${pct}%")"
  fi
fi

# 5-hour quota (supports >100% extra usage)
if [ -n "$fh" ]; then
  pct=$(rnd "$fh")
  if [ -n "$pct" ]; then
    left=$(time_left "$fhr")
    [ -n "$left" ] && left=" $left"
    if (( pct > 100 )); then
      bar=$(printf '█%.0s' {1..8})
      extra=$(( pct - 100 ))
      parts+=" $(ansi 33 "5h:")$(ansi 31 "${bar}${pct}% +${extra}%ex${left}")"
    else
      bar=$(make_bar "$pct")
      parts+=" $(ansi 33 "5h:")$(ansi "$(qcolor "$pct")" "${bar}${pct}%${left}")"
    fi
  fi
fi

# 7-day quota
if [ -n "$sd" ]; then
  pct=$(rnd "$sd")
  if [ -n "$pct" ]; then
    bar=$(make_bar "$pct")
    left=$(time_left "$sdr")
    [ -n "$left" ] && left=" $left"
    parts+=" $(ansi 35 "7d:")$(ansi "$(qcolor "$pct")" "${bar}${pct}%${left}")"
  fi
fi

# Session token usage
if [ -n "$tin" ] || [ -n "$tout" ]; then
  parts+=" $(ansi 90 "Tokens:")$(ansi 0 "in=$(fmt_tokens "$tin") out=$(fmt_tokens "$tout")")"
fi

printf '%s' "$parts"
