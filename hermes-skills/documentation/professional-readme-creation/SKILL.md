---
name: professional-readme-creation
description: Create professional, attention-grabbing README files for technical projects with badges, architecture diagrams, clear sections, and troubleshooting guides. Particularly useful for tools that bridge different systems or enable interoperability.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [documentation, readme, technical-writing, badges, diagrams]
    related_skills: [writing-plans, excalidraw]
---

# Professional README Creation

## Overview

Create comprehensive, professional README files that:
- Grab attention with visual hierarchy and badges
- Clearly explain complex architectures (especially bidirectional communication)
- Provide easy-to-follow installation and usage instructions
- Include troubleshooting guides for common issues
- Follow documentation best practices for open-source projects

## When to Use

Use this skill when:
- Documenting tools that bridge different systems (e.g., Claude Code ↔ Hermes Agent)
- Creating READMEs for developer tools with multiple integration points
- Projects require explaining both synchronous and asynchronous communication paths
- You want to make a strong first impression on potential users/contributors
- The project has non-obvious setup or usage patterns that need clarification

## Core Components

A professional README created with this approach includes:

### 1. Attention-Grabbing Header
- Center-aligned project title with relevant emoji
- Status badges (build, license, language, key integrations)
- Clear value proposition/subtitle

### 2. Architecture Visualization
- Mermaid diagram showing components and data flow
- Clear separation of concerns (different environments/systems)
- Visual representation of sync vs async paths if applicable

### 3. Structured Content Sections
- Overview/Executive Summary (what problem it solves)
- How It Works (detailed mechanism explanation)
- Installation/Setup (prerequisites, one-liner, post-install steps)
- Usage (verification, basic examples, advanced usage)
- Configuration (environment variables, config files)
- Troubleshooting (common issues and solutions)
- Design Notes (architectural decisions explained)
- License and attribution

### 4. Technical Accuracy
- All file paths, commands, and configuration verified
- Clear distinction between automatic and manual steps
- Proper code block formatting and syntax highlighting
- Realistic expected outputs for commands

## Writing Process

### Step 1: Understand the System
- Diagram the components and their interactions
- Identify synchronous vs asynchronous communication paths
- Determine what requires user action vs what happens automatically
- Note any non-obvious dependencies or prerequisites

### Step 2: Gather Technical Details
- Verify exact file paths from the repository structure
- Confirm command syntax and expected outputs
- Check environment variable names and defaults
- Validate installation procedures against actual scripts

### Step 3: Create the Header
- Choose an appropriate emoji that represents the project's purpose
- Create status badges using shields.io syntax
- Write a clear, concise subtitle explaining what the project does

### Step 4: Design the Architecture Diagram
- Use Mermaid syntax for flowcharts or sequence diagrams
- Separate different environments/systems with subgraphs
- Show data flow with clear arrow labels
- Include key files/scripts as nodes where relevant
- Style consistently (colors, shapes, labels)

### Step 5: Write Each Section
- **Overview**: Problem solved and key benefits (2-3 sentences)
- **How It Works**: Detailed explanation of mechanisms (use subsections for different paths)
- **Installation**: Prerequisites, one-liner setup, post-install verification steps
- **Usage**: Verification commands, basic examples, advanced usage patterns
- **Configuration**: Table of environment variables with defaults and purposes
- **Troubleshooting**: Table mapping common issues to solutions
- **Design Notes**: Explain non-obvious architectural decisions
- **License**: Standard license text with pointer to LICENSE file

### Step 6: Review and Refine
- Verify all technical details are accurate
- Check that sections flow logically
- Ensure code blocks are copy-pasteable
- Confirm troubleshooting covers likely user issues
- Make sure the document is scannable with clear headings

## Principles

### Clarity Over Completeness
- Explain concepts clearly before diving into details
- Use analogies when helpful (e.g., "mailbox" for async communication)
- Define acronyms on first use

### Progressive Disclosure
- Start with what users need to know immediately
- Move to advanced usage and configuration later
- Keep troubleshooting separate but accessible

### Visual Hierarchy
- Use emojis sparingly for visual interest (not in headers)
- Center-align key elements for emphasis
- Use tables for structured data (environment variables, troubleshooting)
- Keep code blocks distinct with proper syntax highlighting

### Action-Oriented Language
- Use imperative verbs in instructions ("Run this command", "Check that...")
- Specify exactly what users should see/expect
- Provide verification steps after each major action

## Common Patterns Documented

### Bidirectional Communication Patterns
- Sync path: Direct request/response with session continuity
- Async path 1: Automatic mirroring via hooks/events
- Async path 2: Explicit pushing via skills/scripts
- Message formats (JSONL, headers, etc.)
- Session ID persistence mechanisms

### Tool Bridging Patterns
- Skill-based integration (both systems teach each other skills)
- Hook-based event handling
- Shared state via file system (JSONL transcripts, inboxes)
- Wrapper scripts for consistent interfaces

### Installation Verification
- Health check commands with expected outputs
- Progressive verification (install → verify basic function → try example)
- Clear "next steps" guidance

## Execution

After creating a README using this approach:
1. Save it as `README.md` in the project root
2. Optionally create a plan for implementing any documentation improvements
3. Consider offering to execute improvements using relevant skills

Remember: **A good README makes adoption obvious.** If someone has to guess how to install or use your tool, the documentation is incomplete.