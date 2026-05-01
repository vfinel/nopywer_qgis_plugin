#!/bin/bash

"""
USAGE: 
./release 0.2.4    !! not v0.2.4
TODO:
  - remove 'v' from input 
  - add release commit message ? (instead of 'bumped to...') 
  - add changelog ? (see make a changelog?)
"""

# Exit immediately if a command exits with a non-zero status
set -e

# Check if a version number was provided
if [ -z "$1" ]; then
  echo "❌ Error: Please provide a version number."
  echo "👉 Usage: ./release.sh 0.5.0"
  exit 1
fi

NEW_VERSION=$1
PLUGIN_DIR="nopywer_plugin" # Updated folder name
METADATA_FILE="$PLUGIN_DIR/metadata.txt"

echo "🚀 Preparing release for version v$NEW_VERSION..."

# 1. Update the version inside metadata.txt
# This searches for the line starting with 'version=' and replaces it
sed -i "s/^version=.*/version=$NEW_VERSION/" $METADATA_FILE
echo "✅ Updated metadata.txt to version $NEW_VERSION"

# 2. Stage and commit the change
git add $METADATA_FILE
git commit -m "Bump version to $NEW_VERSION for release"
echo "✅ Committed metadata update"

# 3. Create the git tag
git tag v$NEW_VERSION
echo "✅ Created git tag v$NEW_VERSION"

# 4. Push the commit and the tag to GitHub
echo "⏳ Pushing to GitHub..."
git push origin main
git push origin v$NEW_VERSION

echo "🎉 Success! Release v$NEW_VERSION pushed. GitHub Actions is now building your zip."