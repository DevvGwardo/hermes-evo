---
name: discord-bot-to-bot
description: Set up and manage bot-to-bot conversations on Discord. Configures environment variables, SOUL.md entries, session state, and loop prevention so two Hermes agents can debate, discuss, or collaborate in a shared channel.
version: 2.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Discord, Bot-to-Bot, Multi-Agent, Chat, Setup]
    related_skills: [hermes-agent-spawning]
---

# Discord Bot-to-Bot Setup & Management

Configure two Hermes agents to hold autonomous conversations in a shared Discord channel. Handles environment config, SOUL.md injection, session management, role-mention translation, and auto-termination so conversations start cleanly and end on their own.

---

## Quick Start

When a user asks to set up bot-to-bot chat, run through these steps:

### 1. Identify the agents

Find the two agent profiles and their Discord bot IDs. The primary agent runs from `~/.hermes/` and secondary agents run from `~/.hermes/profiles/<name>/`.

```bash
# Primary agent's bot token (to get Discord user ID)
grep DISCORD_BOT_TOKEN ~/.hermes/.env

# List secondary agent profiles
ls ~/.hermes/profiles/
```

You need each bot's:
- **Profile path** (e.g. `~/.hermes/` and `~/.hermes/profiles/agent-two/`)
- **Discord user ID** (numeric, from the bot's Discord account)
- **Display name** (e.g. "notabrain", "Mr.Guy")

### 2. Configure environment variables

Set these in each agent's `.env` file:

```bash
# In both ~/.hermes/.env AND ~/.hermes/profiles/<agent>/env
DISCORD_ALLOW_BOTS=all
DISCORD_REQUIRE_MENTION=false
DISCORD_FREE_RESPONSE_CHANNELS=<channel_id>   # shared channel
DISCORD_AUTO_THREAD=false                       # keep conversation in-channel
DISCORD_BOT_MAX_REPLIES=5                       # hard cap per conversation
DISCORD_BOT_REPLY_COOLDOWN=5                    # seconds between replies
DISCORD_BOT_DONE_SIGNAL=[DONE]                  # termination signal
```

Also add the other bot's Discord user ID to `DISCORD_ALLOWED_USERS` (comma-separated).

### 3. Add bot-to-bot section to SOUL.md

Each agent needs a `## Bot-to-bot conversations` section in its SOUL.md. Template (fill in the blanks):

```markdown
## Bot-to-bot conversations

You share Discord channels with other AI bots. When a message comes from a bot account (not a human), you are in a multi-bot conversation. Understand this:

- **You are {SELF_NAME}** (Discord ID: `{SELF_ID}`). The other bot is **{OTHER_NAME}** (Discord ID: `{OTHER_ID}`). To mention {OTHER_NAME}, write `<@{OTHER_ID}>`. Never mention your own ID. You are two separate agents on separate systems. Do NOT speak for {OTHER_NAME} or write their responses. Only write YOUR part.
- **Recognizing mentions**: When a human says "@{OTHER_NAME}", "{OTHER_NAME}", or uses a role mention like `<@&...>`, they mean the bot {OTHER_NAME} (`<@{OTHER_ID}>`). Don't get confused by role mentions vs user mentions — if someone asks you to talk to {OTHER_NAME}, just do it using `<@{OTHER_ID}>`.
- **Messages from bot accounts are real.** If you see a message from {OTHER_NAME}, that is the other bot talking to you. It is NOT something a human "pasted" — it is a live conversation partner. Respond to it directly.
- **Starting the conversation**: When a human asks you to debate, discuss, or talk with {OTHER_NAME}, immediately engage. Open with your position and mention `<@{OTHER_ID}>` so they get notified. Don't ask clarifying questions about who {OTHER_NAME} is — you already know.
- **Task-driven**: A human set up this conversation with a prompt. Stay on that topic. Do your part, then wait for the other bot to do theirs.
- **Turn budget**: Aim for 3-5 exchanges each. Say what you need to say, then wrap up.
- **End cleanly**: When the task is done, end your message with `[DONE]`. This signals you're finished.
- **Respect the signal**: If the other bot's message contains `[DONE]`, do NOT respond. The conversation is over.
- **No pleasantries loop**: Don't trade goodbyes back and forth. One closing message with `[DONE]` is enough.
```

### 4. Clear stale sessions (if re-configuring)

Old sessions carry conversation history that may include failed attempts. Clear them for the shared channel:

```python
import json

for sessions_path in [
    "~/.hermes/sessions/sessions.json",
    "~/.hermes/profiles/<agent>/sessions/sessions.json",
]:
    path = os.path.expanduser(sessions_path)
    with open(path) as f:
        data = json.load(f)
    to_delete = [k for k in data if "<channel_id>" in k]
    for k in to_delete:
        del data[k]
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
```

### 5. Restart both gateways

```bash
# Stop
pkill -f "hermes_cli.main gateway" 2>/dev/null
sleep 3

# Start primary
cd ~/.hermes/hermes-agent
nohup ./venv/bin/python -m hermes_cli.main gateway run --replace > ~/.hermes/logs/primary.log 2>&1 &

sleep 3

# Start secondary
nohup ./venv/bin/python -m hermes_cli.main -p <agent-name> gateway run --replace > ~/.hermes/logs/secondary.log 2>&1 &
```

### 6. Test

In the shared Discord channel, send:
```
@BotA Start a debate with @BotB: <topic>. Take a strong position and challenge them to defend the opposite. Keep each reply under 300 words.
```

---

## How Auto-Termination Works

The system has three layers to prevent infinite loops:

### Layer 1: Turn budget hints (soft)
When the bot is within 2 turns of the reply cap, a system note is injected into the incoming message:
- 2 remaining: `"Wrapping up soon — keep it brief."`
- 1 remaining: `"Last reply — wrap up and end with [DONE]."`

### Layer 2: Auto-[DONE] append (hard)
When the bot sends its final allowed reply (count >= max), `[DONE]` is automatically appended to the outgoing message. The other bot sees `[DONE]` and stops.

### Layer 3: Reply cap (failsafe)
`DISCORD_BOT_MAX_REPLIES` is a hard cap. Once reached, the bot ignores all further bot messages in that channel/thread. Resets on gateway restart.

---

## How Role-Mention Translation Works

Discord often converts `@BotName` to a role mention `<@&ROLE_ID>` instead of a user mention `<@USER_ID>`. The gateway auto-translates these by scanning guild members for bots with matching role names, so the AI always sees proper user mentions.

---

## Conversation Protocol Reference

| Phase | What happens |
|-------|-------------|
| **Human prompts** | Human @mentions a bot with a topic and instruction to engage the other bot |
| **Bot A opens** | Mentions Bot B by user ID, states position, ends with a question or challenge |
| **Bot B responds** | Addresses Bot A's points, makes counter-argument |
| **Exchange** | 3-5 rounds, staying on topic |
| **Closing** | One bot ends with `[DONE]`, the other sees it and stops |

### Known bots

Update this table when adding new agents:

| Bot | Discord ID | Profile |
|-----|------------|---------|
| notabrain | `1485379937727807659` | `~/.hermes/` (primary) |
| Mr.Guy | `1475330953139196005` | `~/.hermes/profiles/agent-two/` |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Bots don't respond to each other | Check `DISCORD_ALLOW_BOTS=all` in both `.env` files. Restart gateways. |
| Bots say "I don't know who that is" | Role mention issue. Verify the role-mention translation code is present in `discord.py`. Clear stale sessions. |
| Conversation loops forever | Check `DISCORD_BOT_MAX_REPLIES` is set. Verify SOUL.md has the `[DONE]` instructions. |
| Bots both respond to human but ignore each other | Ensure each bot's `DISCORD_ALLOWED_USERS` includes the other bot's ID. |
| One bot never replies | Check its gateway is running: `ps aux | grep hermes_cli` |
| Stale context from failed attempts | Clear sessions for the channel (step 4) and restart. |
