#!/usr/bin/env sh


# Delete the failed tag locally and on GitHub
git tag -d v0.2.0
git push origin --delete v0.2.0

# Recreate and push the tag
git tag v0.2.0
git push origin main --tags