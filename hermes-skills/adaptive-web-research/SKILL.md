---
name: adaptive-web-research
description: Framework for gathering current web information when encountering obstacles like bot detection, paywalls, or site changes. Adapts approach based on what is encountered.
version: 1.0.0
author: community
license: MIT
metadata:
  hermes:
    tags: [research, web, adaptation, troubleshooting]
    homepage: https://github.com/hermes-ai/adaptive-web-research
prerequisites:
  commands: [browser_navigate, browser_snapshot, browser_type, browser_press]
---
# Adaptive Web Research

A flexible approach to gathering current information from the web when standard methods encounter obstacles.

## When to Use
- Researching fast-moving topics where timeliness matters
- Encountering bot detection, CAPTCHAs, or access restrictions
- Dealing with paywalls, registration walls, or geo-blocking
- Sites with slow loading, timeouts, or changing layouts
- When primary sources are inaccessible but information is still needed

## Core Principles
1. **Start broad, then narrow** - Begin with search engines, then go to specific sources
2. **Have fallback paths** - Know alternative sites and methods for common topics
3. **Adapt to obstacles** - Change tactics based on what you encounter
4. **Verify and cross-reference** - Use multiple sources when possible
5. **Document limitations** - Note when information might be incomplete or biased

## Step-by-Step Approach

### 1. Initial Attempt
- Use search engines (Google, DuckDuckGo, etc.) with specific, timely queries
- Include date constraints if looking for very recent information
- Try different search engines if one seems problematic

### 2. When Encountering Obstacles

**Bot Detection/CAPTCHAs:**
- Switch to less aggressive sites (tech publications, official docs, educational sites)
- Try direct navigation to known quality sources
- Use site-specific search (e.g., `site:technologyreview.com AI news`)
- Vary timing between requests

**Paywalls/Registration Walls:**
- Look for open-access alternatives (arXiv, institutional repositories, blogs)
- Check if abstract/summary provides sufficient information
- Try RSS feeds or AMP versions which sometimes bypass paywalls
- Consider if cached versions or web archives have the content

**Slow Loading/Timeouts:**
- Use `browser_snapshot` first (faster, gets interactive elements)
- Only use `browser_vision` or full snapshots when specifically needed
- Break research into smaller, targeted chunks
- Try text-only versions or reader modes when available

**Changing Site Layouts:**
- Look for semantic patterns (headings, dates, author names) rather than fixed selectors
- Use search within the page for key terms
- Check if the site offers RSS feeds or JSON APIs
- Look for mobile versions which often have simpler layouts

### 3. Source Selection Hierarchy
When primary sources fail, try in this order:
1. **Official sources** (company blogs, project documentation, official reports)
2. **Reputable tech publications** (MIT Tech Review, Ars Technica, The Verge, Wired)
3. **Academic/institutional sources** (university blogs, research lab sites, government publications)
4. **Community sources** (dev blogs, Stack Overflow, GitHub releases, specialist forums)
5. **Aggregators** (Hacker News, Reddit, specialized newsletters)

### 4. Information Extraction
- For articles: extract headline, date, author, key points, and source
- For data: note units, timestamps, methodology, and limitations
- For quotes: capture exact text with attribution
- Always record the URL and access date/time

### 5. Synthesis and Verification
- Cross-check key facts across 2+ independent sources when possible
- Note discrepancies and investigate their causes (different timing, methodologies, etc.)
- Identify potential biases in sources (commercial, ideological, etc.)
- Summarize with clear attribution: "According to [Source] on [Date]..."
- If information is fragmented, state what is known vs. what remains uncertain

## Tools & Techniques
- `browser_navigate`: Go to specific URLs directly
- `browser_snapshot`: Get interactive elements and text content (use `full=false` for speed)
- `browser_type`/`browser_press`: Interact with search boxes, navigation menus
- `browser_vision`: When snapshots don't capture needed visual information (charts, diagrams)
- Multiple source verification: Check the same fact across different site types

## Pitfalls & Solutions
- **Bot detection** → Switch to less trafficked sites, vary request timing, use different access methods
- **Information overload** → Focus on extracting specific data points rather than trying to capture everything
- **Contradictory sources** → Note discrepancies, check dates/methodology, look for consensus or explicit debates
- **Outdated information** → Always check publication/update dates, prioritize very recent sources for fast-moving topics
- **Partial information** → Acknowledge what's missing, note where you looked and didn't find it

## Example: AI News Research (from conversation)
1. **Initial attempt**: Google search for "latest AI news April 2026"
2. **Encountered**: Bot detection page ("Our systems have detected unusual traffic")
3. **Adapted**: Switched to known quality tech publications
4. **Sources used**: 
   - MIT Technology Review AI topic page
   - Ars Technica AI tag page
5. **Extracted**: Headlines, dates, brief summaries from multiple recent articles
6. **Synthesized**: Provided overview of current AI developments across multiple domains

## When to Consider Alternative Approaches
- For deep historical research → consider academic databases or specialized archives
- For scholarly consensus → literature reviews or meta-analyses may be better
- For real-time data → official APIs or WebSocket feeds when available
- For legal/official information → primary sources (govt sites, regulatory bodies) are preferred

This approach is particularly valuable when:
- You need current information and standard search fails
- You're researching topics with high noise-to-signal ratios
- Primary sources are intentionally restrictive (paywalls, rate limits)
- You need to adapt quickly to unknown website behaviors or restrictions