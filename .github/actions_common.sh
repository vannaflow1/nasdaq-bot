#!/usr/bin/env bash
# Commit changed state files back to the repo (retries if another run pushed first).
set -e
git config user.name "nasdaq-bot"
git config user.email "nasdaq-bot@users.noreply.github.com"
git add -A
if git diff --cached --quiet; then echo "no state change"; exit 0; fi
git commit -q -m "state: ${1:-run}"
for i in 1 2 3 4 5; do
  if git pull -q --rebase -X theirs && git push -q; then echo "pushed"; exit 0; fi
  sleep $((i*5))
done
echo "push failed"; exit 1
