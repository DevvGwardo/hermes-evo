---
name: message-claude
description: >
  Send a message directly to the user's Claude Code session by appending it to
  the Claude inbox at ~/.hermes-chat/inbox.jsonl. Use this whenever the user
  asks you to "tell Claude", "message Claude", "send this to Claude", "notify
  Claude", "let Claude know", or similar — or when you finish autonomous work
  and want to proactively report the result to Claude Code. Claude will see
  the message the next time it runs the hermes-chat skill's `check` command.
category: messaging
---

# message-claude

## What this skill does

Delivers a text message from Hermes to the user's Claude Code assistant. The
message lands in a local JSONL mailbox that Claude Code reads on demand via
its `hermes-chat` skill.

Use this as a one-way push channel: fire-and-forget. Claude will not reply
through this channel — if you need a reply, the user (or Claude, on its next
turn) will send one back to you via the Hermes API (`api_server` platform).

## When to use it

Trigger this skill whenever the user says any of:

- "tell Claude X" / "message Claude X" / "send this to Claude"
- "let Claude know ..." / "notify Claude ..."
- "ping Claude with the result" / "report back to Claude when done"
- "push this to Claude" / "drop this in Claude's inbox"

Also use it proactively in autonomous contexts: if you've just finished a
scheduled task, long-running background job, or cron-triggered work whose
result Claude needs to see, send a brief summary via message-claude.

## How to use it

Run the `message-claude` command with the text to deliver. The script lives
at `~/.hermes-chat/bin/message-claude` and is a thin shell wrapper that
appends a JSONL entry.

### Single-line message

```bash
~/.hermes-chat/bin/message-claude "deploy finished — 3 tests failed, see ~/deploy.log"
```

### Multi-line / long message (use stdin)

```bash
~/.hermes-chat/bin/message-claude <<'EOF'
Morning report:
- Overnight cron ran at 03:00, all checks passed
- New issue #482 needs triage
- Disk usage on /var is at 87%
EOF
```

### From a pipeline

```bash
tail -n 20 ~/some.log | ~/.hermes-chat/bin/message-claude
```

## Output

On success the script prints:
```
delivered to Claude inbox (N total entries)
```
where N is the running count of messages in the inbox.

Exit code 0 = delivered; non-zero = failure (empty message, write error,
etc.). If it fails, say so plainly and do NOT retry with an empty message.

## Keep messages concise

Claude reads the inbox as a flat log — long rambling entries are hard to
scan. Aim for:
- A clear first sentence summarizing what happened
- Bullet points for details if needed
- Links or file paths Claude can open for deeper inspection

If you're tempted to dump 200 lines of log output, write the log to a file
first and just message Claude the path + a one-sentence summary.

## Do not use this for

- **Asking Claude questions that need a synchronous answer.** This is
  one-way. If you need a synchronous response, wait for Claude to message
  you via the Hermes API.
- **Trivial acknowledgments** ("ok", "done") when no one asked. Claude
  doesn't need a play-by-play.
- **Sensitive data.** The inbox is a plaintext file on disk.
