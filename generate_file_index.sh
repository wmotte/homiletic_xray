#!/bin/bash
#
# Generate file_index.json for the web interface
# This script can be run independently to update the index without re-running analyses
#
# Usage: ./generate_file_index.sh
#

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Directories
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOCS_DIR="${SCRIPT_DIR}/docs"
INDEX_FILE="${DOCS_DIR}/file_index.json"

echo -e "${YELLOW}Generating file index for web interface...${NC}"

# Check if docs directory exists
if [ ! -d "${DOCS_DIR}" ]; then
    echo -e "${YELLOW}Warning: Docs directory not found: ${DOCS_DIR}${NC}"
    mkdir -p "${DOCS_DIR}"
fi

# Create JSON array of filenames from docs directory
# Look for analysis JSON files (exclude index files and HTML)
TEMP_LIST=$(mktemp)
find "${DOCS_DIR}" -maxdepth 1 -name "*_*_*.json" -type f ! -name "file_index.json" -exec basename {} \; | sort > "${TEMP_LIST}"

FILE_COUNT=$(wc -l < "${TEMP_LIST}" | tr -d ' ')

if [ "${FILE_COUNT}" -eq 0 ]; then
    echo "[]" > "${INDEX_FILE}"
else
    echo "[" > "${INDEX_FILE}"
    while IFS= read -r filename; do
        if [ -n "$filename" ]; then
            echo "  \"${filename}\"," >> "${INDEX_FILE}"
        fi
    done < "${TEMP_LIST}"
    # Remove trailing comma from last entry and close array
    sed -i.bak '$ s/,$//' "${INDEX_FILE}" && rm -f "${INDEX_FILE}.bak"
    echo "]" >> "${INDEX_FILE}"
fi

rm -f "${TEMP_LIST}"

echo -e "${GREEN}✓ Index file created: ${INDEX_FILE}${NC}"
echo -e "${GREEN}✓ Total files indexed: ${FILE_COUNT}${NC}"
echo ""
