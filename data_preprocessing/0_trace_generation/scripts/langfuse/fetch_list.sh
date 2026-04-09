#!/bin/bash

OUTPUT_FILE="all_observations.jsonl"
BASE_URL="<your_base_url>"
AUTH_HEADER='<your_auth_header>'
CURSOR=""

THREADS=10          # How many concurrent requests?
BATCH_SIZE=10       # How many pages to schedule at once?

# Clean up previous run
rm -f "$OUTPUT_FILE"
rm -rf temp_pages
mkdir -p temp_pages

# Export variables so the subshells (xargs) can see them
export BASE_URL AUTH_HEADER

# 1. Define the worker function
fetch_page() {
    local PAGE=$1
    local URL="$BASE_URL/api/public/observations?limit=50&page=$PAGE"
    local TEMP_FILE="temp_pages/page_${PAGE}.json"

    # echo "Fetching Page $PAGE..." # Optional: too much noise in parallel

    RESPONSE=$(curl -s -X GET "$URL" \
        -H "Authorization: Basic $AUTH_HEADER" \
        -H "Content-Type: application/json")

    # validation: check if valid json and contains data
    if ! echo "$RESPONSE" | grep -q "data"; then
        echo "Error on Page $PAGE"
        return 1
    fi

    DATA=$(echo "$RESPONSE" | jq -c '.data[]')

    if [ -z "$DATA" ]; then
        # Create empty file to signal no data
        touch "$TEMP_FILE.empty"
    else
        echo "$DATA" > "$TEMP_FILE"
        echo "  -> Page $PAGE downloaded."
    fi
}

export -f fetch_page

# 2. Main Loop (Batch Processing)
CURRENT_PAGE=1

while : ; do
    echo "--- Starting Batch: Pages $CURRENT_PAGE to $((CURRENT_PAGE + BATCH_SIZE - 1)) ---"
    
    # Generate sequence for this batch and run in parallel
    seq "$CURRENT_PAGE" "$((CURRENT_PAGE + BATCH_SIZE - 1))" | \
    xargs -P "$THREADS" -I {} bash -c 'fetch_page "{}"'

    # 3. Check for stop condition
    # If any page in this batch was empty, we need to stop.
    # We check if an ".empty" marker file was created.
    if ls temp_pages/*.empty 1> /dev/null 2>&1; then
        echo "Found empty page in this batch. Stopping..."
        break
    fi

    # Prepare next batch
    CURRENT_PAGE=$((CURRENT_PAGE + BATCH_SIZE))
done

# 4. Merge and Cleanup
echo "Merging files..."
# Sort numerically (sort -n) so page 1, 2, 10 are in order, not 1, 10, 2
find temp_pages -name "page_*.json" | sort -V | xargs cat >> "$OUTPUT_FILE"

# Clean up temp folder
rm -rf temp_pages

echo "Done! Total items: $(wc -l < "$OUTPUT_FILE")"