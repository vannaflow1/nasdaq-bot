#!/usr/bin/env bash
# Commit changed state files back to the repo (retries if another run pushed first).
# If the rebase stops on a conflict that -X theirs cannot settle (typically knowledge/announce.json: deleted upstream by
# learn-post after posting, modified here), this run's version of every conflicted file is kept and the rebase continues,
# so hours of results are never lost to a one-file conflict. A rebase that still cannot finish is aborted before retrying.
set -e
git config user.name "nasdaq-bot"
git config user.email "nasdaq-bot@users.noreply.github.com"
git add -A
if git diff --cached --quiet; then echo "no state change"; exit 0; fi
git commit -q -m "state: ${1:-run}"

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
echo "push failed"; exit 1
