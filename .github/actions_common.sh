#!/usr/bin/env bash
# Commit changed state files back to the repo (retries if another run pushed first).
# If the rebase stops on a conflict that -X theirs cannot settle (typically knowledge/announce.json: deleted upstream by
# learn-post after posting, modified here), this run's version of every conflicted file is kept and the rebase continues,
# so hours of results are never lost to a one-file conflict. A rebase that still cannot finish is aborted before retrying.
#
# 15 Nov 2026 fixes (plain words):
#  * status.json is merged KEY BY KEY (tools/status_merge.py), so one job can no longer overwrite another job's entry.
#  * A commit that could not be pushed is retried. Before, the second call saw "nothing new to commit" and reported
#    success while the results were never uploaded (the prop search lost every run from 25 Oct to 15 Nov this way).
#  * Files close to GitHub's 100 MB limit are reported loudly: GitHub refuses the whole push when one file is over it.
set -e
git config user.name "nasdaq-bot"
git config user.email "nasdaq-bot@users.noreply.github.com"
git config merge.statusjson.name "status.json key-by-key merge"
git config merge.statusjson.driver "python3 tools/status_merge.py %O %A %B"

git add -A
committed=0
if ! git diff --cached --quiet; then git commit -q -m "state: ${1:-run}"; committed=1; fi
ahead=$(git rev-list --count "@{u}..HEAD" 2>/dev/null || echo 0)
if [ "$committed" = "0" ] && [ "$ahead" = "0" ]; then echo "no state change"; exit 0; fi
[ "$committed" = "0" ] && echo "retrying an earlier commit that was never pushed ($ahead ahead)"

big=$(git ls-files -z | xargs -0 -r stat -c '%s %n' 2>/dev/null | awk '$1 > 99614720 {printf "%s (%.1f MB) ", $2, $1/1048576}')
[ -n "$big" ] && echo "::error::files at or near GitHub's 100 MB limit - the push will be refused: $big"

settle_rebase() {
  local n=0
  while [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ]; do
    n=$((n+1)); [ $n -gt 20 ] && return 1
    local files; files=$(git diff --name-only --diff-filter=U)
    [ -z "$files" ] && return 1
    echo "resolving rebase conflict (keeping this run's version): $files"
    while IFS= read -r f; do
      if git cat-file -e ":3:$f" 2>/dev/null; then git checkout --theirs -- "$f" && git add -- "$f"
      else git checkout --ours -- "$f" 2>/dev/null && git add -- "$f" || true; fi   # deleted here: keep the upstream copy (never delete data)
    done <<< "$files"
    GIT_EDITOR=true git rebase --continue >/dev/null 2>&1 || true
  done
  return 0
}

for i in 1 2 3 4 5; do
  if git pull -q --rebase -X theirs || settle_rebase; then
    if git push -q; then echo "pushed"; exit 0; fi
  else
    git rebase --abort 2>/dev/null || true
  fi
  sleep $((i*5))
done
echo "::error::push failed after 5 tries - this run's results are NOT in the repo yet"; exit 1
