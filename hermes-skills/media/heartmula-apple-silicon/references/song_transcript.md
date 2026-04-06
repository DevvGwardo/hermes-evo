---
name: song_transcript
description: Full transcript of creating "These Users Are Made For Onboardin'" — a parody song about being banned from opencheeks.com
---

# Song: "These Users Are Made For Onboardin'"

**Style:** 1960s campy female vocal, smoky lounge, big band brass, comic spoken asides, tongue-in-cheek delivery, moderate tempo  
**Exclude:** Modern production, autotune, heavy reverb

---

```
[Intro]
(Boots walkin' music)

[Verse 1]
You were only onboardin' users in the door
Givin' all the new folks logins by the score
Then one day you learned what admin law is for
You're banned baby banned

Sent you off to opencheeks dot com
Thought you'd help some folks get settled in their home
Now you're banned from onboarding that's the crime you've done
You're banned baby banned

[Chorus]
These users are made for onboardin'
And the docs are just for readin'
And they're walkin' all over you

[Verse 2]
Violation one improper greeting tone
You said hey what's up and that did not atone
Violation two you worked on your own phone
You're banned baby banned

Violation three the Khaki Pants Brigade
Decided your account was not what HR made
Violation four you gave a helper an upgrade
You're banned baby banned

[Chorus]
These users are made for onboardin'
And the handbook's just for readin'
And they're walkin' all over you

[Bridge]
Opencheeks dot com yeah they're sendin' you mail
Welcome to the help center here's your welcome trail
But the welcome trail just leads back to the jail
Where you're banned baby banned

[Verse 3]
You did everything by the book by the page
You were helpful you were friendly you engaged
But the algorithm flagged your helpful rage
You're banned baby banned

Now you're lurkin' on the forum you once knew
Tryna find the admin who would sponsor you
Every thread just ends with account banned at the top of the queue
You're banned baby banned

[Final Chorus]
These users were made for onboardin'
And the admins just kept readin'
And they walked all over you

[Outro]
Banned from opencheeks
You're banned from onboarding users
What a stupid thing to do
```

## Setup transcript summary

The full setup transcript is in `/Users/devgwardo/hermes-pixel-agents/song_transcript.md`.

Key setup steps:
1. Created venv with Python 3.10 via `uv`
2. Installed HeartMuLa and dependencies
3. Upgraded `transformers` and `datasets` to fix conflicts
4. Downloaded 14.4GB in model checkpoints (3B model + codec)
5. Applied 4 source patches for Apple Silicon compatibility
6. Generated song using `--mula_device mps --codec_device mps`
7. Patched `torchaudio.save` → `soundfile.write` for MP3 export

Output: `~/hermes-pixel-agents/output_banned.mp3` (3min, 48kHz stereo)
