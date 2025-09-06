#!/usr/bin/env bash
set -euo pipefail

BUILD_DIR="site"
BRANCH="gh-pages"

if [ ! -d "$BUILD_DIR" ]; then
  echo "No $BUILD_DIR directory to publish."
  exit 1
fi

# Ensure we are at repo root
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "Run this inside your git repo root."
  exit 1
}

# Create or update gh-pages using worktree (no keys needed for viewers)
git fetch origin || true

if git show-ref --verify --quiet refs/heads/$BRANCH; then
  git branch -D $BRANCH
fi
git checkout --orphan $BRANCH
git reset

# Stage the site/ contents only
git --work-tree="$BUILD_DIR" add --all
git --work-tree="$BUILD_DIR" commit -m "Publish static site"
git push origin HEAD:$BRANCH -f
git checkout -

echo "Pushed $BUILD_DIR to $BRANCH."
echo "Now enable GitHub Pages: Settings → Pages → Build and deployment → Deploy from branch → gh-pages / (root)."
