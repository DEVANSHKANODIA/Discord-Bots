# Discord Music Bot (Single File)

This is a single-file Python Discord music bot with high-quality audio, slash commands, buttons, autoplay radio, and Spotify playlist parsing (maps tracks to YouTube).

## Quick Start

1. **Install system dependency**: FFmpeg (required)
   - Windows: https://www.gyan.dev/ffmpeg/builds/ (add `ffmpeg.exe` to PATH)
   - macOS: `brew install ffmpeg`
   - Linux: use your package manager.

2. **Create a bot** at the Discord Developer Portal and copy the **Bot Token**. Enable **MESSAGE CONTENT INTENT**.

3. **Clone / download** this project and install Python deps:
   ```bash
   pip install -r requirements.txt
   ```

4. **(Optional) Spotify support**:
   - Create a Spotify app at https://developer.spotify.com/
   - Set env vars:
     - `SPOTIFY_CLIENT_ID`
     - `SPOTIFY_CLIENT_SECRET`

5. **Set env vars and run**:
   ```bash
   set DISCORD_TOKEN=YOUR_TOKEN   # Windows (PowerShell: $env:DISCORD_TOKEN="...")
   python music_bot.py
   ```
   or on macOS/Linux:
   ```bash
   export DISCORD_TOKEN=YOUR_TOKEN
   python3 music_bot.py
   ```

## Commands
- `/join` – join your voice channel
- `/play <query|url>` – YouTube/Spotify link or search; Spotify items are matched to YouTube
- `/pause`, `/resume`, `/skip`, `/stop`, `/leave`
- `/queue`, `/np`, `/remove <index>`, `/shuffle`
- `/loop <off|one|all>`
- `/autoplay <on|off>`
- `/volume <0-200>`
- `/seek <mm:ss|seconds>`

Buttons appear on the **Now Playing** message for quick control.

## Notes
- Discord does not allow streaming DRM-protected Spotify audio directly. This bot reads Spotify playlists to discover tracks, then plays them from YouTube.
- Make sure FFmpeg is installed and accessible from your PATH.
