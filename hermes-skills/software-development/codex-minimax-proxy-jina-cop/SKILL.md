---
name: codex-minimax-proxy-jina-cop
description: Jina Reader cop integration for codex-minimax-proxy — free URL fetching with no API key
---

# codex-minimax-proxy Jina Cop Integration

## Context
Proxy at `~/codex-minimax-proxy/proxy.mjs` that routes Codex/MiniMax calls. Jina Reader added as free cop layer for URL fetching — no API key needed.

## Architecture

### URL Cop Flow
```
User message with URL → detect URL → inject web_fetch tool → MiniMax call
                                                    ↓
                                              Jina Reader
                                              (r.jina.ai/<url>)
                                                    ↓
                                              Clean markdown
                                                    ↓
                                              Model receives content
```

### Functions

**jinaRead(url)** — primary cop fetcher
- GET request to `https://r.jina.ai/<url>`
- Returns clean markdown, strips nav/ads
- 80k char limit, 20s timeout
- Best for: documentation, articles, GitHub READMEs, Stack Overflow

**rawFetch(url, method, headers, body)** — fallback
- Used for POST/PUT/PATCH/DELETE
- Also used when Jina returns error
- Returns raw HTTP response

**executeWebFetch(url, rawBody)** — router
- `GET || HEAD` → jinaRead
- Everything else → rawFetch

### Endpoints

**POST /v1/chat/completions** + URL in messages
→ URL detected → web_fetch injected → Jina fetches → response enriched

**POST /v1/responses** + URL in input
→ Same as above, Responses API path

**GET /cop?url=https://...**
→ Standalone URL copping, returns markdown directly

### GitHub Auth
When `gh` CLI is installed, Authorization header auto-injected for github.com URLs.

## Verification
```bash
# Standalone cop
curl "http://localhost:4000/cop?url=https://example.com"

# Full round-trip with MiniMax
curl -X POST http://localhost:4000/v1/responses \
  -H "Content-Type: application/json" \
  -d '{"input": "Summarize https://github.com/openai/codex"}'

# Health
curl http://localhost:4000/health

# Test suite
cd ~/codex-minimax-proxy && node test.cjs
```

## Key Files
- `~/codex-minimax-proxy/proxy.mjs` — main proxy
- `~/.hermes/.env` — MINIMAX_API_KEY source
- `~/codex-minimax-proxy/test.cjs` — test suite
