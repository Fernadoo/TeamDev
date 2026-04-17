#!/usr/bin/env bash
# Find PR template files in the repository.
#
# Usage:
#   find-pr-template.sh [repo_root]
#
# Searches standard locations for PULL_REQUEST_TEMPLATE files.
# Outputs JSON to stdout:
#   {"found": true, "path": "/path/to/template", "multiple": false}
#   {"found": true, "paths": [...], "multiple": true}
#   {"found": false}
#
# Exit codes:
#   0 - template(s) found
#   1 - no template found

set -euo pipefail

REPO_ROOT="${1:-.}"

TEMPLATES=()

# Check standard locations in order of precedence
CANDIDATES=(
    ".github/PULL_REQUEST_TEMPLATE.md"
    ".github/pull_request_template.md"
    "PULL_REQUEST_TEMPLATE.md"
    "pull_request_template.md"
    "docs/PULL_REQUEST_TEMPLATE.md"
    "docs/pull_request_template.md"
)

for candidate in "${CANDIDATES[@]}"; do
    full_path="$REPO_ROOT/$candidate"
    if [ -f "$full_path" ]; then
        TEMPLATES+=("$full_path")
    fi
done

# Check template directory
TEMPLATE_DIR="$REPO_ROOT/.github/PULL_REQUEST_TEMPLATE"
if [ -d "$TEMPLATE_DIR" ]; then
    while IFS= read -r -d '' tpl; do
        TEMPLATES+=("$tpl")
    done < <(find "$TEMPLATE_DIR" -type f -name "*.md" -print0 2>/dev/null)
fi

# Also do a broad search if nothing found yet
if [ ${#TEMPLATES[@]} -eq 0 ]; then
    while IFS= read -r -d '' tpl; do
        TEMPLATES+=("$tpl")
    done < <(find "$REPO_ROOT" -maxdepth 3 \( -iname "PULL_REQUEST_TEMPLATE*" -o -iname "pull_request_template*" \) -type f -print0 2>/dev/null)
fi

if [ ${#TEMPLATES[@]} -eq 0 ]; then
    echo '{"found": false}'
    exit 1
elif [ ${#TEMPLATES[@]} -eq 1 ]; then
    # Use python for safe JSON encoding if available, fallback to printf
    if command -v python3 &>/dev/null; then
        python3 -c "import json; print(json.dumps({'found': True, 'path': '''${TEMPLATES[0]}''', 'multiple': False}))"
    else
        printf '{"found": true, "path": "%s", "multiple": false}\n' "${TEMPLATES[0]}"
    fi
    exit 0
else
    if command -v python3 &>/dev/null; then
        python3 -c "
import json, sys
paths = sys.argv[1:]
print(json.dumps({'found': True, 'paths': paths, 'multiple': True}))
" "${TEMPLATES[@]}"
    else
        printf '{"found": true, "paths": ['
        first=true
        for t in "${TEMPLATES[@]}"; do
            if [ "$first" = true ]; then first=false; else printf ','; fi
            printf '"%s"' "$t"
        done
        printf '], "multiple": true}\n'
    fi
    exit 0
fi
