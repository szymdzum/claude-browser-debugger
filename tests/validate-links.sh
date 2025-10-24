#!/bin/bash
# validate-links.sh - Check all markdown links resolve
# Created for feature 005-docs-reorganization

set -euo pipefail

echo "Validating internal links in documentation..."
echo ""

BROKEN=0
CHECKED=0

# Extract all markdown links from key files
# Pattern: [text](path) but exclude http/https URLs
FILES_TO_CHECK=(
  "docs/index.md"
  "README.md"
  "CLAUDE.md"
  "SKILL.md"
)

# Also check all spec files
while IFS= read -r file; do
  FILES_TO_CHECK+=("$file")
done < <(find specs -name "*.md" 2>/dev/null || true)

# Function to check if a link resolves
check_link() {
  local source_file="$1"
  local link="$2"
  local source_dir
  local resolved_path

  # Skip external URLs
  if [[ "$link" =~ ^https?:// ]]; then
    return 0
  fi

  # Skip anchors and fragments
  if [[ "$link" =~ ^# ]]; then
    return 0
  fi

  # Get directory of source file
  source_dir=$(dirname "$source_file")

  # Remove anchor fragments from link
  link="${link%%#*}"

  # Resolve relative path
  if [[ "$link" == /* ]]; then
    # Absolute path from repo root
    resolved_path="$link"
  elif [[ "$link" == ../* ]]; then
    # Parent directory reference
    resolved_path="$source_dir/$link"
  else
    # Relative to source directory
    resolved_path="$source_dir/$link"
  fi

  # Normalize path by resolving .. and .
  resolved_path=$(python3 -c "import os; print(os.path.normpath('$resolved_path'))" 2>/dev/null || echo "$resolved_path")

  # Check if file or directory exists
  if [[ ! -f "$resolved_path" ]] && [[ ! -d "$resolved_path" ]]; then
    echo "❌ BROKEN: $source_file -> $link"
    echo "   Resolved to: $resolved_path (NOT FOUND)"
    BROKEN=$((BROKEN + 1))
  fi

  CHECKED=$((CHECKED + 1))
}

# Process each file
for file in "${FILES_TO_CHECK[@]}"; do
  if [[ ! -f "$file" ]]; then
    continue
  fi

  # Extract links using ripgrep
  while IFS= read -r line; do
    # Extract link from markdown format [text](link)
    link=$(echo "$line" | sed -n 's/.*](\([^)]*\)).*/\1/p')
    if [[ -n "$link" ]]; then
      check_link "$file" "$link"
    fi
  done < <(rg '\[.*?\]\([^)]+\)' "$file" -o 2>/dev/null || true)
done

echo ""
echo "===================================="
echo "Link validation complete"
echo "===================================="
echo "Checked: $CHECKED links"
echo "Broken: $BROKEN links"

if [[ $BROKEN -eq 0 ]]; then
  echo ""
  echo "✅ All internal links are valid!"
  exit 0
else
  echo ""
  echo "❌ Found $BROKEN broken link(s) - please fix before proceeding"
  exit 1
fi
