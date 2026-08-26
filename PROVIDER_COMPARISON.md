# Provider Comparison: Gemini vs Groq

**Date:** 2026-08-26
**Status:** Gemini selected as primary provider

## Summary

Tested Gemini Flash and Groq (openai/gpt-oss-120b) for intent extraction and response generation. **Gemini selected** due to better JSON schema compliance and structured output quality.

## Test Results

### Intent Extraction

| Query | Gemini (3.7-flash) | Groq (gpt-oss-120b) |
|-------|-------------------|---------------------|
| "get me to a nearby starbucks" | Valid JSON, correct schema | Valid JSON, but `search_terms` as string |
| "how about a market" | Valid JSON, `replace_search` mode | Truncated output (reasoning tokens) |
| "the second one" | Valid JSON, `selected_index: 2` | N/A |
| "navigate there" | Valid JSON, `select` mode | N/A |
| "is it open now" | Valid JSON, `refine` mode | N/A |

### Response Generation

| Metric | Gemini | Groq |
|--------|--------|------|
| Quality | Natural, detailed | Natural, detailed |
| Latency | ~3-4s | ~0.9s |
| Tokens (in/out) | 71/92 | 172/288 |

### Schema Issues with Groq

1. **`search_terms`** returned as string instead of array
2. **`follow_up_mode`** uses different values (`"explicit"`, `"replace"` vs `"select"`, `"replace_search"`)
3. **Reasoning tokens** eat into output budget, causing truncation
4. **Qwen 27B** spends all tokens on thinking, never outputs JSON

### Free Tier Comparison

| Provider | RPM | Tokens/min | Requests/day | Credit Card |
|----------|-----|------------|--------------|-------------|
| Gemini Flash | 10-15 | 250K-1M | 1,500 | No |
| Groq (gpt-oss-120b) | 30 | 6,000 | ~14,400 | No |

## Decision

**Gemini Flash** selected because:
- JSON output matches our schema exactly (array types, correct enum values)
- No reasoning tokens wasting output budget
- Structured output is more reliable for intent extraction
- 1,500 req/day sufficient for current usage

**Groq consideration:** Could be used as fallback for response generation (faster, cheaper) but schema mismatches make it unsuitable for intent extraction without prompt engineering work.

## Models Tested on Groq

| Model | Status | Notes |
|-------|--------|-------|
| llama-3.3-70b-versatile | Not available | Model not on free tier |
| qwen/qwen3.6-27b | Failed | All tokens spent on thinking |
| openai/gpt-oss-120b | Worked | Schema mismatches, truncation |
| openai/gpt-oss-20b | Not tested | |
| allam-2-7b | Not tested | 4K context too small |
