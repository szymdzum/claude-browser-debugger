# Filter Flag Guide: Selective Network Body Capture

**Purpose:** Learn when and how to use the `--filter` flag for capturing specific network response bodies

**Use Case:** Reduce storage and processing overhead by capturing only relevant API responses

---

## Overview

By default, the network monitor captures request/response metadata (URLs, status codes, headers, timing) but **not response bodies**. This keeps logs small and fast.

The `--filter` flag enables **selective body capture** for requests matching a pattern.

---

## Basic Usage

### Syntax

```bash
python3 -m scripts.cdp.cli.main orchestrate "URL" DURATION OUTPUT --filter=PATTERN
```

### Examples

**Capture marketing API responses:**
```bash
python3 -m scripts.cdp.cli.main orchestrate "http://localhost:3000" 30 /tmp/test.log --filter=marketing
```

**Capture all /api/ endpoints:**
```bash
python3 -m scripts.cdp.cli.main orchestrate "http://localhost:3000" 30 /tmp/test.log --filter=api
```

**Capture specific endpoint:**
```bash
python3 -m scripts.cdp.cli.main orchestrate "http://localhost:3000" 30 /tmp/test.log --filter=customer/register
```

---

## How It Works

### Without --filter (Default)

**Captured:**
- Request URL, method, headers
- Response status, headers, timing
- Request body (if present)

**Not Captured:**
- Response bodies

**Result:** Minimal log size, fast processing

### With --filter=pattern

**Captured:**
- All of the above, PLUS
- Response bodies for URLs matching `pattern`

**Pattern Matching:**
- Searches URL path for the pattern
- Case-sensitive substring match
- Example: `--filter=api` matches:
  - ✅ `https://example.com/api/users`
  - ✅ `https://example.com/v1/api/data`
  - ❌ `https://example.com/API/users` (wrong case)

---

## Common Patterns

### Capture All API Responses

```bash
--filter=api
```

**Matches:**
- `/api/customer/register`
- `/v1/api/products`
- `/graphql/api`

---

### Capture Specific Domain

```bash
--filter=example.com
```

**Matches:**
- `https://api.example.com/users`
- `https://example.com/api/data`

---

### Capture Specific Endpoint

```bash
--filter=/customer/register
```

**Matches:**
- `https://example.com/customer/register`
- `https://api.example.com/v1/customer/register`

---

### Capture by Resource Type

```bash
--filter=json
```

**Matches:**
- `https://example.com/data.json`
- `https://api.example.com/users?format=json`

---

## When to Use --filter

### ✅ Use --filter When:

1. **Debugging specific API failures** - Capture only failing endpoint bodies
2. **Investigating data corruption** - Capture specific API responses for validation
3. **Performance testing** - Capture timing + body size for specific endpoints
4. **Token/auth debugging** - Capture authentication endpoint responses

### ❌ Don't Use --filter When:

1. **General browsing** - Default mode sufficient for most testing
2. **Large file downloads** - Bodies can overwhelm storage
3. **Streaming responses** - May not capture complete data
4. **Binary content** - Images, videos won't be useful in text logs

---

## Storage & Performance

### Body Size Limits

**Default:** Response bodies truncated at **1MB** per request

**Impact:**
- Without --filter: ~10KB per request (metadata only)
- With --filter: ~1KB to 1MB per matching request

**Example:**
- 100 requests, 10 match filter, avg 50KB body
- Log size: (90 × 10KB) + (10 × 50KB) = **1.4MB** total

### Performance Tips

1. **Use specific patterns** - `--filter=customer/register` not `--filter=api`
2. **Limit duration** - Shorter sessions = fewer captured requests
3. **Monitor log size** - Use `ls -lh OUTPUT_FILE` during capture
4. **Combine with --idle** - Stop capture when traffic stops

---

## Advanced Patterns

### Multiple Keywords (OR Logic)

**Not directly supported.** Use multiple sessions:

```bash
# Session 1: Capture marketing
python3 -m scripts.cdp.cli.main orchestrate URL 30 /tmp/marketing.log --filter=marketing

# Session 2: Capture customer
python3 -m scripts.cdp.cli.main orchestrate URL 30 /tmp/customer.log --filter=customer
```

### Exclude Pattern (NOT Logic)

**Not supported.** Filter is include-only.

**Workaround:** Capture all, post-process with jq/grep to exclude

---

## Examples by Use Case

### Debug Failed Login API

```bash
python3 -m scripts.cdp.cli.main orchestrate "http://localhost:3000/login" 60 /tmp/login-debug.log \
  --filter=auth/login --include-console
```

**Why:** Captures auth endpoint body + console errors

---

### Investigate Missing Customer Data

```bash
python3 -m scripts.cdp.cli.main orchestrate "http://localhost:3000/dashboard" 120 /tmp/customer-debug.log \
  --filter=customer --mode=headed --include-console
```

**Why:** Captures all customer API responses during manual interaction

---

### Performance Test API Endpoint

```bash
python3 -m scripts.cdp.cli.main orchestrate "http://localhost:3000/api-test" 30 /tmp/perf.log \
  --filter=/v1/products --idle=5
```

**Why:** Captures response times + body sizes for specific endpoint

---

## Analyzing Captured Bodies

### Extract Response Bodies from Log

```bash
# Find all captured bodies
grep '"responseBody":' /tmp/test.log

# Extract specific response
jq '.responseBody' /tmp/test.log | head -1
```

### Search Body Content

```bash
# Find errors in responses
grep -A 10 '"responseBody":' /tmp/test.log | grep -i error

# Find specific data
jq 'select(.url | contains("customer")) | .responseBody' /tmp/test.log
```

### Count Captured Bodies

```bash
grep -c '"responseBody":' /tmp/test.log
```

---

## Troubleshooting

### No Bodies Captured Despite --filter

**Possible Causes:**
1. Pattern doesn't match any URLs
2. Responses are empty (204 No Content)
3. Timing issue (responses after capture stops)

**Solution:**
```bash
# Verify pattern matches URLs in log
grep '"url":' /tmp/test.log | grep PATTERN

# Check for empty responses
grep '"status": 204' /tmp/test.log
```

---

### Log File Too Large

**Symptom:** Log file grows to several GB

**Solutions:**
1. Use more specific filter pattern
2. Reduce session duration
3. Use `--idle=N` to auto-stop when quiet

**Emergency:**
```bash
# Kill capture early
pkill -f cdp-network
```

---

### Binary Response Bodies Garbled

**Symptom:** Response bodies show gibberish for images/files

**Solution:** Don't use --filter for binary content

**Alternative:** Capture timing metadata only (default mode)

---

## Quick Reference

| Pattern | Captures | Use For |
|---------|----------|---------|
| `--filter=api` | All /api/ endpoints | General API debugging |
| `--filter=auth` | Auth endpoints | Login/token issues |
| `--filter=customer` | Customer data APIs | Data validation |
| `--filter=/specific/path` | Exact path match | Targeted debugging |
| `--filter=.json` | JSON file responses | Data file debugging |

---

## Related Documentation

- [Workflow Guide](./workflow-guide.md) - Complete headed mode workflow
- [Network Monitor](../../cdp-network-with-body.py) - Filter implementation
- [Stage Test Results](../002-stage-test-result.md) - Original findings
