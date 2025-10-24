#!/bin/bash
# Test script to validate URL validation research findings
# Demonstrates curl behavior with different scenarios

set -euo pipefail

echo "=== URL Validation Research Testing ==="
echo "Testing curl behavior for different scenarios"
echo ""

test_url() {
  local description="$1"
  local url="$2"
  local method="${3:-GET}"

  echo "---"
  echo "Test: $description"
  echo "URL: $url"
  echo "Method: $method"

  local start_time=$(date +%s.%N)
  local http_code
  local curl_exit

  if [[ "$method" == "HEAD" ]]; then
    http_code=$(curl -I --max-time 5 --connect-timeout 3 --location --silent \
      --output /dev/null --write-out "%{http_code}" "$url" 2>&1)
    curl_exit=$?
  else
    http_code=$(curl --max-time 5 --connect-timeout 3 --location --silent \
      --output /dev/null --write-out "%{http_code}" "$url" 2>&1)
    curl_exit=$?
  fi

  local end_time=$(date +%s.%N)
  local duration=$(echo "$end_time - $start_time" | bc)

  echo "HTTP Code: $http_code"
  echo "Exit Code: $curl_exit"
  echo "Duration: ${duration}s"

  case $curl_exit in
    0) echo "Result: ✓ curl succeeded" ;;
    3) echo "Result: ✗ URL malformed" ;;
    6) echo "Result: ✗ DNS resolution failed" ;;
    7) echo "Result: ✗ Connection refused" ;;
    28) echo "Result: ✗ Operation timeout" ;;
    35) echo "Result: ✗ SSL handshake failed" ;;
    52) echo "Result: ✗ Empty reply from server" ;;
    *) echo "Result: ✗ curl error $curl_exit" ;;
  esac

  if [[ $curl_exit -eq 0 ]]; then
    if [[ "$http_code" =~ ^(200|201|301|302|303|307|308)$ ]]; then
      echo "Status: ✓ VALID (would accept)"
    elif [[ "$http_code" =~ ^[45][0-9]{2}$ ]]; then
      echo "Status: ⚠ WARNING (HTTP error, prompt user)"
    else
      echo "Status: ✗ INVALID (unexpected status)"
    fi
  fi

  echo ""
}

# Test 1: Valid URL (should accept)
test_url "Valid URL (200)" "https://example.com" "GET"

# Test 2: Redirect (should accept)
test_url "Redirect (302)" "https://httpbin.org/redirect/2" "GET"

# Test 3: HTTP Error (should prompt)
test_url "Client Error (404)" "https://httpbin.org/status/404" "GET"

# Test 4: Server Error (should prompt)
test_url "Server Error (500)" "https://httpbin.org/status/500" "GET"

# Test 5: DNS failure (should reject)
test_url "DNS Failure" "http://nonexistent-domain-xyz-test-123.invalid" "GET"

# Test 6: Connection timeout (should reject - will take 3 seconds)
echo "Test: Connection Timeout (will take ~3 seconds)"
test_url "Connection Timeout" "http://192.0.2.1:9999" "GET"

# Test 7: HEAD vs GET comparison on problematic endpoint
echo "=== HEAD vs GET Comparison ==="
test_url "httpstat.us - HEAD request" "https://httpstat.us/200" "HEAD"
test_url "httpstat.us - GET request" "https://httpstat.us/200" "GET"

echo "==="
echo "Testing complete!"
echo ""
echo "Summary of findings:"
echo "- GET requests are more reliable than HEAD"
echo "- Valid status codes: 2xx and 3xx"
echo "- curl exit code 0 doesn't mean HTTP success (check status separately)"
echo "- Connection timeout (exit 28) vs DNS failure (exit 6) are distinct"
echo "- Timeouts: --connect-timeout 3 (fail fast) + --max-time 5 (overall)"
