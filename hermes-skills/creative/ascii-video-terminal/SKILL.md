---
name: ascii-video-terminal
description: Generative ASCII art backgrounds for terminal. Use standalone, as a desktop wallpaper, or integrated with Hermes for animated backdrop while chatting.
triggers:
  - "ascii background"
  - "generative ascii"
  - "terminal wallpaper"
  - "ascii art loop"
  - "live ascii background"
  - "pipes screensaver"
  - "cmatrix"
  - "terminal screensaver"
  - "hermes ascii"
  - "hermes with ascii"
  - "ascii hermes"
---

# ASCII Art Backgrounds for Terminal

Generative, looping ASCII art that runs as a live background behind your CLI/TUI work.

## Installation

```bash
# macOS
brew install cmatrix mpv
brew install pipes-sh  # pipes screensaver

# Ubuntu/Debian
sudo apt install cmatrix mpv

# Arch
sudo pacman -S cmatrix mpv

# pip
pip install asciimatics
```

---

## 1. Quick Start — Generative ASCII Loops

### Classic Matrix Rain
```bash
cmatrix -b -u 9 -s
```
`-b` bold, `-u 9` speed (1-10, lower=faster), `-s` screensaver mode (exits on keypress)

### Rotating Pipes (classic)
```bash
pipes.sh
```

### Rotating Pipes (modern, more options)
```bash
pipes.sh -t 5    # 5 pipe types
pipes.sh -f 120  # 120 FPS
pipes.sh -l 40   # max pipe length
pipes.sh -r R    # random start direction
```

### Audio Visualizer (generates from system audio)
```bash
# Install cava
brew install cava

# Run with default settings
cava
```

### Custom Generative Scripts (Python + curses)

See Section 3 below for advanced generative art scripts.

---

## 2. As a Persistent Background (detach from terminal)

### Using `screen` (recommended)

```bash
# Start cmatrix in a named screen session
screen -S ascii-bg -dm bash -c 'cmatrix -b -u 9 -s'

# Detach: Ctrl+A, D

# Reattach anytime
screen -r ascii-bg

# List all screens
screen -ls
```

### Using `tmux`

```bash
tmux new-session -d -s ascii-bg 'cmatrix -b -u 9 -s'
tmux attach-session -t ascii-bg
```

### Using `nohup` (truly background)

```bash
nohup cmatrix -b -u 9 -s > /dev/null 2>&1 &
```

---

## 3. Generative ASCII Art Scripts

These produce algorithmic, looping ASCII art — not playing back recorded video.

### Plasma Wave
```bash
#!/usr/bin/env bash
# Plasma wave effect - sine-based generative art
# Save as: ~/ascii-scripts/plasma.sh

cols=$(tput cols)
lines=$(tput lines)
chars=' .:-=+*#%@'

while true; do
  for ((y=0; y<lines; y++)); do
    for ((x=0; x<cols; x++)); do
      v=$(echo "s($x*0.1)+s($y*0.1)+s(($x+$y)*0.05)+s($x*0.02)" | bc -l 2>/dev/null | head -1)
      i=$(echo "($v + 4) * 10 / 8" | bc 2>/dev/null | cut -d. -f1)
      [ "$i" -lt 0 ] && i=0
      [ "$i" -gt 10 ] && i=10
      printf '%s' "${chars:$i:1}"
    done
    echo
  done
  sleep 0.05
done
```

### Particle Flow
```python
#!/usr/bin/env python3
# Particle flow - save as ~/ascii-scripts/particle_flow.py

import curses
import random
import math
import time

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    sh, sw = stdscr.getmaxyx()
    w = curses.initscr()
    curses.start_color()
    curses.use_default_colors()

    particles = []
    for _ in range(150):
        particles.append({
            'x': random.random() * sw,
            'y': random.random() * sh,
            'vx': (random.random() - 0.5) * 0.5,
            'vy': (random.random() - 0.5) * 0.5,
            'c': random.randint(1, 7)
        })

    trail = [[' ' for _ in range(sw)] for _ in range(sh)]
    chars = '.,-~:;=!*#$@'

    while True:
        try:
            stdscr.erase()
            new_trail = [[' ' for _ in range(sw)] for _ in range(sh)]

            for p in particles:
                nx = int(p['x']) % sw
                ny = int(p['y']) % sh
                idx = int((math.sin(p['x']*0.1) + 1) * len(chars) / 2)
                new_trail[ny][nx] = chars[min(idx, len(chars)-1)]

                p['x'] += p['vx']
                p['y'] += p['vy']

                if p['x'] < 0: p['x'] += sw
                if p['x'] > sw: p['x'] -= sw
                if p['y'] < 0: p['y'] += sh
                if p['y'] > sh: p['y'] -= sh

                p['vx'] += (random.random() - 0.5) * 0.1
                p['vy'] += (random.random() - 0.5) * 0.1
                p['vx'] *= 0.99
                p['vy'] *= 0.99

            for y in range(sh):
                stdscr.addstr(y, 0, ''.join(new_trail[y]))

            stdscr.refresh()
            time.sleep(0.03)
        except curses.break:
            break

if __name__ == '__main__':
    curses.wrapper(main)
```

### Spiral Galaxy
```bash
#!/usr/bin/env bash
# Spiral galaxy - save as ~/ascii-scripts/spiral.sh

cols=$(tput cols)
rows=$(tput lines)
center_c=$((cols/2))
center_r=$((rows/2))

t=0
while true; do
  clear
  for ((r=0; r<rows; r++)); do
    line=""
    for ((c=0; c<cols; c++)); do
      dx=$((c - center_c))
      dy=$((r - center_r))
      dist=$(echo "sqrt($dx*$dx + $dy*$dy)" | bc -l)
      angle=$(echo "a($dy/($dx+0.0001)) + $t" | bc -l)
      spiral=$(echo "s($angle * 3 + $dist * 0.1 + $t)" | bc -l)
      v=$(echo "($spiral + 1) / 2" | bc -l | cut -d. -f1)
      [ -z "$v" ] && v=0
      [ "$v" -gt 9 ] && v=9
      char=' .:-=+*#%@'[v]
      line="${line}${char}"
    done
    echo "$line"
  done
  t=$(echo "$t + 0.2" | bc -l)
  sleep 0.1
done
```

### Fire/Wave Effect
```python
#!/usr/bin/env python3
# Fire effect - save as ~/ascii-scripts/fire.py

import curses
import random
import time

def main(stdscr):
    curses.curs_set(0)
    sh, sw = stdscr.nodelay(True)
    w = curses.initscr()
    curses.start_color()
    curses.use_default_colors()

    chars = ' .:-=+*#%@'
    fire = [[0 for _ in range(sw)] for _ in range(sh)]

    while True:
        fire[sh-1] = [random.randint(0, 9) for _ in range(sw)]

        for r in range(sh-2, -1, -1):
            for c in range(sw):
                val = fire[r+1][c]
                val += fire[r+1][max(0, c-1)]
                val += fire[r+1][min(sw-1, c+1)]
                fire[r][c] = val // 3

        stdscr.erase()
        for r in range(sh):
            stdscr.addstr(r, 0, ''.join(chars[min(v, 9)] for v in fire[r]))
        stdscr.refresh()
        time.sleep(0.05)

if __name__ == '__main__':
    curses.wrapper(main)
```

### Conway's Game of Life (ASCII)
```bash
#!/usr/bin/env bash
# Conway's Game of Life - save as ~/ascii-scripts/life.sh

cols=$(tput cols)
rows=$(tput lines)

declare -A grid
for ((r=0; r<rows; r++)); do
  for ((c=0; c<cols; c++)); do
    [ $((RANDOM % 10)) -eq 0 ] && grid[$r,$c]=1 || grid[$r,$c]=0
  done
done

render() {
  for ((r=0; r<rows; r++)); do
    line=""
    for ((c=0; c<cols; c++)); do
      [ "${grid[$r,$c]}" -eq 1 ] && line+='*' || line+=' '
    done
    echo "$line"
  done
}

count_neighbors() {
  local r=$1 c=$2 count=0
  for dr in -1 0 1; do
    for dc in -1 0 1; do
      [ "$dr" -eq 0 -a "$dc" -eq 0 ] && continue
      nr=$(( (r + dr + rows) % rows ))
      nc=$(( (c + dc + cols) % cols ))
      [ "${grid[$nr,$nc]}" -eq 1 ] && ((count++))
    done
  done
  echo $count
}

while true; do
  clear
  render
  declare -A newgrid
  for ((r=0; r<rows; r++)); do
    for ((c=0; c<cols; c++)); do
      n=$(count_neighbors $r $c)
      if [ "${grid[$r,$c]}" -eq 1 ]; then
        [ "$n" -eq 2 -o "$n" -eq 3 ] && newgrid[$r,$c]=1 || newgrid[$r,$c]=0
      else
        [ "$n" -eq 3 ] && newgrid[$r,$c]=1 || newgrid[$r,$c]=0
      fi
    done
  done
  for key in "${!newgrid[@]}"; do grid[$key]=${newgrid[$key]}; done
  sleep 0.1
done
```

---

## 4. Running Generative Scripts as Background

```bash
# Make scripts executable
chmod +x ~/ascii-scripts/*.sh ~/ascii-scripts/*.py

# Run plasma as background (screen)
screen -S ascii-bg -dm bash -c '~/ascii-scripts/plasma.sh'

# Run particle flow (tmux)
tmux new-session -d -s ascii-bg '~/ascii-scripts/particle_flow.py'

# Run all effects (with random switching)
screen -S ascii-bg -dm bash -c '
while true; do
  scripts=(plasma.sh spiral.sh life.sh)
  script=${scripts[RANDOM % ${#scripts[@]}]}
  ~/ascii-scripts/$script &
  sleep 30
  kill %1 2>/dev/null
done
'
```

---

## 5. mpv Video as Looping ASCII Background

For pre-recorded video loops (e.g., a synthwave music video you want looping as your "desktop"):

```bash
brew install mpv

# Loop a video file as ASCII art, silent, fullscreen
mpv /path/to/loop.mp4 --vo=caca --loop=inf --no-audio --fs --caca-darkbg

# YouTube video loop (get a looping music video)
mpv "https://youtube.com/watch?v=VIDEO_ID" --vo=caca --loop=inf --no-audio --ytdl

# Daemonized
screen -S ascii-bg -dm mpv /path/to/video.mp4 --vo=caca --loop=inf --no-audio --fs
```

**For best video-to-ASCII results**, use videos with:
- High contrast scenes
- Neon/synthwave aesthetic (dark bg + bright elements)
- Slow camera movement (too fast = visual noise)

Search for "lofi aesthetic video" or "synthwave loop" on YouTube and pipe to mpv --vo=caca.

---

## 6. Hermes + ASCII (Integrated Session)

Run Hermes with an animated ASCII art backdrop in the same terminal window using tmux split panes.

### Start Hermes with ASCII Wallpaper

```bash
~/ascii-scripts/hermes-ascii.sh start
```

### Available Animations

```bash
~/ascii-scripts/hermes-ascii.sh start plasma.sh      # Synthwave plasma (default)
~/ascii-scripts/hermes-ascii.sh start spiral.sh      # Galaxy vortex
~/ascii-scripts/hermes-ascii.sh start starfield.py   # 3D starfield warp
~/ascii-scripts/hermes-ascii.sh start matrix_rain.py # Matrix rain
~/ascii-scripts/hermes-ascii.sh start fire.py        # ASCII fire
~/ascii-scripts/hermes-ascii.sh start life.sh        # Conway's Game of Life
~/ascii-scripts/hermes-ascii.sh start particle_flow.py # Vector field particles
```

### Controls

```bash
tmux attach -t hermes-ascii          # Attach to the session
~/ascii-scripts/hermes-ascii.sh stop  # Stop
~/ascii-scripts/hermes-ascii.sh cycle # Switch to next animation
```

While attached to the tmux session:
```
Ctrl+B, ↓   # Jump to Hermes pane (bottom - where you type)
Ctrl+B, ↑   # Jump to wallpaper pane (top - visual only)
Ctrl+B, D   # Detach
```

### How It Works

- tmux session "hermes-ascii" with two panes in one window
- Top pane (35%): animated ASCII art, non-interactive
- Bottom pane (65%): Hermes running normally
- No borders, clean full-screen look

---

## 7. Auto-Start on Terminal Open

The ASCII background auto-starts every time you open a terminal. It runs in a detached `screen` session so it's always there behind your work. Scripts cycle automatically every 45 seconds.

### Quick Aliases (already added to ~/.zshrc)

```bash
ha              # Shortcut to hermes-ascii launcher
ha-start        # Start Hermes with ASCII wallpaper
ha-stop         # Stop the session
ha-attach       # Attach to running session
```

### One-Line Setup

```bash
mkdir -p ~/ascii-scripts && cat > ~/ascii-scripts/ascii-bg-launcher.sh << 'LAUNCHER'
#!/usr/bin/env bash
scripts=("$HOME/ascii-scripts/plasma.sh" "$HOME/ascii-scripts/spiral.sh" "$HOME/ascii-scripts/fire.py" "$HOME/ascii-scripts/life.sh")
[ ! -f "${scripts[0]}" ] && exec cmatrix -b -u 9 -s
while true; do for s in "${scripts[@]}"; do [ -f "$s" ] && "$s"; done; done
LAUNCHER
chmod +x ~/ascii-scripts/*.sh ~/ascii-scripts/*.py 2>/dev/null
grep -q "ascii-bg" ~/.zshrc 2>/dev/null || cat >> ~/.zshrc << 'ZSHRC'

# ASCII Art Background Auto-Start
if ! screen -ls | grep -q ascii-bg; then
  screen -S ascii-bg -dm bash -c ~/ascii-scripts/ascii-bg-launcher.sh
fi
ZSHRC
screen -S ascii-bg -dm bash -c ~/ascii-scripts/ascii-bg-launcher.sh 2>/dev/null
echo "Done. Restart terminal or run: source ~/.zshrc"
```

### What This Does

1. Creates `~/ascii-scripts/` with a launcher that cycles through all effect scripts
2. Falls back to `cmatrix` if no custom scripts exist
3. Adds a check to `~/.zshrc` that starts the background on every new terminal
4. The `screen -ls | grep -q ascii-bg` guard prevents duplicate sessions
5. Starts it immediately (no need to restart terminal)

### Control the Background

```bash
# See it
screen -r ascii-bg

# Detach: Ctrl+A, D

# Restart with latest scripts
screen -S ascii-bg -X quit
screen -S ascii-bg -dm bash -c ~/ascii-scripts/ascii-bg-launcher.sh

# Kill completely
screen -S ascii-bg -X quit

# List running
screen -ls | grep ascii-bg
```

### Adding More Effect Scripts

Drop any `.sh` or `.py` script into `~/ascii-scripts/` — the launcher picks them up automatically on next terminal open. No config changes needed.

---

## 7. Quick Reference

| Effect | Command |
|--------|---------|
| Matrix rain | `cmatrix -b -u 9 -s` |
| Pipes | `pipes.sh -f 120` |
| Audio visualizer | `cava` |
| Video as ASCII | `mpv video.mp4 --vo=caca` |
| Plasma (bash) | `~/ascii-scripts/plasma.sh` |
| Particle flow | `~/ascii-scripts/particle_flow.py` |
| Spiral galaxy | `~/ascii-scripts/spiral.sh` |
| Fire effect | `~/ascii-scripts/fire.py` |
| Game of Life | `~/ascii-scripts/life.sh` |

---

## 7. Keyboard Controls (while running)

| Key | Action |
|-----|--------|
| `q` | Quit |
| `Ctrl+C` | Force quit |
| `Ctrl+A, D` | Detach screen session |

For mpv video playback:
| Key | Action |
|-----|--------|
| `Space` | Pause/Resume |
| `q` | Quit |
