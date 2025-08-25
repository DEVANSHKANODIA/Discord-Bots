#!/usr/bin/env python3
"""
Discord Music Bot (single-file) with Slash Commands, Buttons, Autoplay, and Spotify playlist support.

Features
- /play (YouTube/Spotify URL or search), /pause, /resume, /skip, /stop, /queue, /np, /remove, /shuffle,
  /loop [off|one|all], /autoplay [on|off], /volume [0-200], /seek [mm:ss], /join, /leave
- Buttons GUI on the "Now Playing" message (Pause/Resume, Skip, Stop, Loop, Shuffle, Autoplay, Volume +/-)
- High-quality audio via FFmpeg + Opus (48kHz). Uses yt-dlp for source extraction.
- Spotify playlist/album/track parsing via Spotipy (maps tracks to YouTube by title/artist).
- Autoplay "radio": if queue ends, finds related videos for the last track.
- Single Python file for the bot logic. Requires FFmpeg installed on your system.

Setup
1) Python 3.10+ recommended.
2) Install dependencies: pip install -r requirements.txt
3) Install FFmpeg and make sure it's in your PATH (ffmpeg -version).
4) Create a Discord bot at https://discord.com/developers/applications, enable the "MESSAGE CONTENT INTENT".
5) Add the bot to your server with permissions: bot + applications.commands; voice connect/speak, send messages, etc.
6) Set environment variables (recommended):
   - DISCORD_TOKEN=<your discord bot token>
   - SPOTIFY_CLIENT_ID=<optional for Spotify support>
   - SPOTIFY_CLIENT_SECRET=<optional for Spotify support>
7) Run: python music_bot.py  (or whatever you name this file).
"""
import os
import re
import io
import math
import time
import json
import asyncio
from typing import Optional, List, Dict, Any, Tuple

import discord
from discord import app_commands
from discord.ext import commands

import yt_dlp

# Spotify is optional
_SPOTIFY_AVAILABLE = True
try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
except Exception:
    _SPOTIFY_AVAILABLE = False

# ========================== Config ==========================

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.guilds = True
INTENTS.voice_states = True

# FFmpeg options for stable streaming
FFMPEG_OPTIONS = {
    "before_options": "-nostdin -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn -bufsize 8192k -ar 48000 -ac 2"
}

YTDL_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "nocheckcertificate": True,
    "ignoreerrors": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "extract_flat": False,
    "cachedir": False,
    "noplaylist": True,
    "geo_bypass": True,
    "concurrent_fragment_downloads": 1,
}

YTDL_SEARCH_OPTS = dict(YTDL_OPTS, **{
    "noplaylist": True,
    "default_search": "ytsearch",
})

# Loop modes
LOOP_OFF, LOOP_ONE, LOOP_ALL = "off", "one", "all"

# ========================== Helpers ==========================

def human_time(seconds: float) -> str:
    seconds = int(max(0, seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"

def parse_time_str(ts: str) -> Optional[int]:
    m = re.match(r"^(?:(\d+):)?(\d{1,2}):(\d{2})$", ts.strip())
    if m:
        h = int(m.group(1) or 0)
        mm = int(m.group(2))
        ss = int(m.group(3))
        return h*3600 + mm*60 + ss
    m = re.match(r"^(\d{1,2}):(\d{2})$", ts.strip())
    if m:
        mm = int(m.group(1))
        ss = int(m.group(2))
        return mm*60 + ss
    try:
        return int(ts)
    except:
        return None

def fmt_track_md(track: Dict[str, Any]) -> str:
    base = f"**{track.get('title','Unknown')}**"
    if track.get("uploader"):
        base += f" — *{track['uploader']}*"
    dur = track.get("duration")
    if dur:
        base += f" `{human_time(dur)}`"
    return base

def ensure_ffmpeg() -> None:
    import shutil
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg is not installed or not in PATH. Please install FFmpeg.")

# ========================== YTDL Source ==========================

class YTDLSource(discord.PCMVolumeTransformer):
    ytdl = yt_dlp.YoutubeDL(YTDL_OPTS)

    def __init__(self, source, *, data: Dict[str, Any], volume: float = 0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get("title")
        self.url = data.get("webpage_url")
        self.uploader = data.get("uploader")
        self.thumbnail = data.get("thumbnail")
        self.duration = data.get("duration")
        self.is_live = data.get("is_live", False)
        self.webpage_url = data.get("webpage_url")
        self.id = data.get("id")

    @classmethod
    async def from_url(cls, url: str, *, loop: asyncio.AbstractEventLoop = None, stream: bool = True, start_time: Optional[int] = None):
        loop = loop or asyncio.get_running_loop()
        def extract():
            return cls.ytdl.extract_info(url, download=not stream)
        data = await loop.run_in_executor(None, extract)
        if data is None:
            raise RuntimeError("Failed to extract audio.")
        if "entries" in data:
            data = next((e for e in data["entries"] if e), None)
            if data is None:
                raise RuntimeError("No playable entries found.")
        if stream:
            url2 = data.get("url")
        else:
            url2 = cls.ytdl.prepare_filename(data)
        # Seek
        before = FFMPEG_OPTIONS["before_options"]
        if start_time:
            before = f"{before} -ss {int(start_time)}"
        source = discord.FFmpegOpusAudio(url2, **{**FFMPEG_OPTIONS, "before_options": before})
        return cls(source, data=data)

    @classmethod
    async def search_yt(cls, query: str):
        loop = asyncio.get_running_loop()
        def _search():
            with yt_dlp.YoutubeDL(YTDL_SEARCH_OPTS) as ydl:
                return ydl.extract_info(query, download=False)
        data = await loop.run_in_executor(None, _search)
        if data and "entries" in data and data["entries"]:
            return data["entries"][0]
        return None

# ========================== Spotify Helpers ==========================

class SpotifyHelper:
    def __init__(self):
        self.enabled = False
        if _SPOTIFY_AVAILABLE:
            cid = os.getenv("SPOTIFY_CLIENT_ID")
            secret = os.getenv("SPOTIFY_CLIENT_SECRET")
            if cid and secret:
                auth = SpotifyClientCredentials(client_id=cid, client_secret=secret)
                self.sp = spotipy.Spotify(auth_manager=auth, requests_timeout=10, retries=3)
                self.enabled = True

    def is_spotify_url(self, url: str) -> bool:
        return "open.spotify.com" in url

    def extract_queries_from_url(self, url: str) -> List[str]:
        """Return a list of 'Artist - Track' strings to search on YouTube."""
        if not self.enabled:
            raise RuntimeError("Spotify support not configured. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET.")
        m = re.search(r"open\.spotify\.com/(track|playlist|album)/([A-Za-z0-9]+)", url)
        if not m:
            raise RuntimeError("Unsupported Spotify URL.")
        kind, sid = m.group(1), m.group(2)
        results = []
        if kind == "track":
            t = self.sp.track(sid)
            name = t["name"]
            artists = ", ".join(a["name"] for a in t["artists"])
            results.append(f"{artists} - {name}")
        elif kind == "album":
            alb = self.sp.album(sid)
            for t in alb["tracks"]["items"]:
                name = t["name"]
                artists = ", ".join(a["name"] for a in t["artists"])
                results.append(f"{artists} - {name}")
        elif kind == "playlist":
            pl = self.sp.playlist(sid)
            # playlist could be long; cap to avoid rate limits
            for item in pl["tracks"]["items"]:
                track = item.get("track")
                if not track:
                    continue
                name = track["name"]
                artists = ", ".join(a["name"] for a in track["artists"])
                results.append(f"{artists} - {name}")
        return results

SPOTIFY = SpotifyHelper()

# ========================== Player ==========================

class GuildPlayer:
    def __init__(self, bot: commands.Bot, guild: discord.Guild):
        self.bot = bot
        self.guild = guild
        self.queue: asyncio.Queue = asyncio.Queue()
        self.next_event = asyncio.Event()
        self.current: Optional[YTDLSource] = None
        self.volume: float = 0.5
        self.loop_mode: str = LOOP_OFF
        self.autoplay: bool = True
        self.history: List[Dict[str, Any]] = []
        self.np_message: Optional[discord.Message] = None
        self.skip_votes: set[int] = set()
        self.lock = asyncio.Lock()
        self.player_task = bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            self.next_event.clear()
            try:
                if self.loop_mode == LOOP_ONE and self.current is not None:
                    source = await YTDLSource.from_url(self.current.webpage_url, stream=True)
                else:
                    try:
                        item = await asyncio.wait_for(self.queue.get(), timeout=300)
                    except asyncio.TimeoutError:
                        # Inactivity disconnect
                        vc = self.guild.voice_client
                        if vc and vc.is_connected():
                            await vc.disconnect(force=True)
                        self.current = None
                        self.np_message = None
                        continue
                    source = item
                self.current = source
                self.current.volume = self.volume
                self.skip_votes.clear()

                # Play
                vc = self.guild.voice_client
                if not vc or not vc.is_connected():
                    await asyncio.sleep(0.5)
                    continue
                def after_play(err):
                    if err:
                        print(f"Error in playback: {err}")
                    self.bot.loop.call_soon_threadsafe(self.next_event.set)
                vc.play(self.current, after=after_play)

                await self.announce_now_playing()
                await self.next_event.wait()

                # Remember history
                if self.current and self.loop_mode != LOOP_ONE:
                    self.history.append(self.current.data)

                # Loop all: put it back
                if self.loop_mode == LOOP_ALL and self.current:
                    await self.queue.put(await YTDLSource.from_url(self.current.webpage_url, stream=True))

                # Autoplay: queue a related track if queue empty
                if self.autoplay and self.queue.empty() and self.current:
                    rel = await self.get_related(self.current.data)
                    if rel:
                        info = await YTDLSource.search_yt(rel)
                        if info:
                            src = await YTDLSource.from_url(info.get("webpage_url") or info.get("url"), stream=True)
                            await self.queue.put(src)

                self.current = None
            except Exception as e:
                print("Player loop error:", e)
                await asyncio.sleep(2)

    async def get_related(self, data: Dict[str, Any]) -> Optional[str]:
        # Try to use 'related' field from yt_dlp if available; else fallback to a search by title & uploader.
        rel = None
        if data:
            rels = data.get("related") or []
            if isinstance(rels, list) and rels:
                rel = rels[0].get("url")
        if rel:
            return rel
        title = data.get("title")
        uploader = data.get("uploader") or ""
        if title:
            return f"{title} {uploader}"
        return None

    def get_queue_snapshot(self) -> List[Dict[str, Any]]:
        lst = []
        try:
            while True:
                item = self.queue.get_nowait()
                lst.append(item)
        except asyncio.QueueEmpty:
            pass
        for it in lst:
            self.queue.put_nowait(it)
        return [it.data for it in lst]

    async def ensure_voice(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client if interaction.guild else None
        if vc and vc.channel:
            return vc
        if interaction.user is None or not isinstance(interaction.user, discord.Member):
            raise commands.CommandError("Join a voice channel first.")
        if interaction.user.voice is None or interaction.user.voice.channel is None:
            raise commands.CommandError("You need to join a voice channel first.")
        channel = interaction.user.voice.channel
        return await channel.connect(self_deaf=True, reconnect=True)

    async def announce_now_playing(self):
        ch = self.find_text_channel()
        if not ch or not self.current:
            return
        view = ControlsView(self)
        embed = self.make_now_playing_embed()
        try:
            if self.np_message and self.np_message.channel.id == ch.id:
                await self.np_message.edit(embed=embed, view=view)
            else:
                self.np_message = await ch.send(embed=embed, view=view)
        except discord.HTTPException:
            pass

    def find_text_channel(self) -> Optional[discord.TextChannel]:
        # Prefer the system channel or first text channel
        if self.guild.system_channel and self.guild.system_channel.permissions_for(self.guild.me).send_messages:
            return self.guild.system_channel
        for ch in self.guild.text_channels:
            perms = ch.permissions_for(self.guild.me)
            if perms.send_messages:
                return ch
        return None

    def make_now_playing_embed(self) -> discord.Embed:
        cur = self.current
        embed = discord.Embed(title="Now Playing", description=fmt_track_md(cur.data) if cur else "Nothing", color=0x2ecc71)
        if cur and cur.thumbnail:
            embed.set_thumbnail(url=cur.thumbnail)
        embed.add_field(name="Volume", value=f"{int(self.volume*100)}%", inline=True)
        embed.add_field(name="Loop", value=self.loop_mode, inline=True)
        embed.add_field(name="Autoplay", value="on" if self.autoplay else "off", inline=True)
        q = self.get_queue_snapshot()
        if q:
            preview = "\n".join([f"{i+1}. {fmt_track_md(t)}" for i, t in enumerate(q[:10])])
            if len(q) > 10:
                preview += f"\n…and {len(q)-10} more"
            embed.add_field(name="Up Next", value=preview, inline=False)
        return embed

# ========================== Buttons View ==========================

class ControlsView(discord.ui.View):
    def __init__(self, player: GuildPlayer):
        super().__init__(timeout=None)
        self.player = player

    @discord.ui.button(emoji="⏯️", style=discord.ButtonStyle.secondary)
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client if interaction.guild else None
        if not vc:
            return await interaction.response.send_message("Not in a voice channel.", ephemeral=True)
        if vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Resumed.", ephemeral=True)
        else:
            vc.pause()
            await interaction.response.send_message("⏸️ Paused.", ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client if interaction.guild else None
        if not vc or not vc.is_playing():
            return await interaction.response.send_message("Nothing to skip.", ephemeral=True)
        vc.stop()
        await interaction.response.send_message("⏭️ Skipped.", ephemeral=True)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client if interaction.guild else None
        if vc:
            vc.stop()
            await interaction.response.send_message("⏹️ Stopped.", ephemeral=True)

    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.secondary)
    async def loop_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        modes = [LOOP_OFF, LOOP_ONE, LOOP_ALL]
        cur = self.player.loop_mode
        nxt = modes[(modes.index(cur)+1) % len(modes)]
        self.player.loop_mode = nxt
        await interaction.response.send_message(f"Loop mode: **{nxt}**", ephemeral=True)
        await self.player.announce_now_playing()

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary)
    async def shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        items = []
        try:
            while True:
                items.append(self.player.queue.get_nowait())
        except asyncio.QueueEmpty:
            pass
        import random
        random.shuffle(items)
        for it in items:
            self.player.queue.put_nowait(it)
        await interaction.response.send_message("🔀 Shuffled queue.", ephemeral=True)
        await self.player.announce_now_playing()

    @discord.ui.button(emoji="🤖", style=discord.ButtonStyle.secondary)
    async def autoplay_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player.autoplay = not self.player.autoplay
        await interaction.response.send_message(f"Autoplay: **{'on' if self.player.autoplay else 'off'}**", ephemeral=True)
        await self.player.announce_now_playing()

    @discord.ui.button(emoji="🔉", style=discord.ButtonStyle.secondary)
    async def vol_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player.volume = max(0.0, self.player.volume - 0.1)
        if self.player.current:
            self.player.current.volume = self.player.volume
        await interaction.response.send_message(f"Volume: {int(self.player.volume*100)}%", ephemeral=True)
        await self.player.announce_now_playing()

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary)
    async def vol_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player.volume = min(2.0, self.player.volume + 0.1)
        if self.player.current:
            self.player.current.volume = self.player.volume
        await interaction.response.send_message(f"Volume: {int(self.player.volume*100)}%", ephemeral=True)
        await self.player.announce_now_playing()

# ========================== Bot ==========================

class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned_or("!"), intents=INTENTS)
        # Removed self.tree assignment because discord.py v2 already has it
        self.players: Dict[int, GuildPlayer] = {}


    def get_player(self, guild: discord.Guild) -> GuildPlayer:
        if guild.id not in self.players:
            self.players[guild.id] = GuildPlayer(self, guild)
        return self.players[guild.id]

    async def setup_hook(self):
        # Persist views
        self.add_view(ControlsView(GuildPlayer(self, self.guilds[0])) if self.guilds else ControlsView(GuildPlayer(self, None)))  # dummy to register
        await self.tree.sync()

bot = MusicBot()

# ========================== Slash Commands ==========================

@bot.tree.command(name="join", description="Make the bot join your voice channel.")
async def join(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    player = bot.get_player(interaction.guild)
    await player.ensure_voice(interaction)
    await interaction.followup.send("Joined your voice channel.", ephemeral=True)

@bot.tree.command(name="play", description="Play a song by URL or search query (YouTube/Spotify supported).")
@app_commands.describe(query="YouTube/Spotify URL or search terms")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer(thinking=True)
    ensure_ffmpeg()
    player = bot.get_player(interaction.guild)
    vc = await player.ensure_voice(interaction)

    to_add: List[YTDLSource] = []

    try:
        if SPOTIFY.is_spotify_url(query):
            queries = SPOTIFY.extract_queries_from_url(query)
            added = 0
            for q in queries:
                info = await YTDLSource.search_yt(q)
                if not info:
                    continue
                src = await YTDLSource.from_url(info.get("webpage_url") or info.get("url"), stream=True)
                to_add.append(src)
                added += 1
            if added == 0:
                await interaction.followup.send("Couldn't resolve any tracks from that Spotify link.", ephemeral=True)
                return
        else:
            info = await YTDLSource.search_yt(query)
            if not info:
                await interaction.followup.send("No results found.", ephemeral=True)
                return
            src = await YTDLSource.from_url(info.get("webpage_url") or info.get("url"), stream=True)
            to_add.append(src)
    except Exception as e:
        await interaction.followup.send(f"Error: {e}", ephemeral=True)
        return

    for src in to_add:
        await player.queue.put(src)

    if not vc.is_playing() and player.current is None:
        # Trigger the loop immediately
        if player.next_event.is_set():
            player.next_event.clear()
        vc.stop()

    if len(to_add) == 1:
        await interaction.followup.send(f"Queued: {fmt_track_md(to_add[0].data)}")
    else:
        await interaction.followup.send(f"Queued **{len(to_add)}** tracks.")

@bot.tree.command(name="pause", description="Pause playback.")
async def pause(interaction: discord.Interaction):
    vc = interaction.guild.voice_client if interaction.guild else None
    if not vc or not vc.is_playing():
        return await interaction.response.send_message("Nothing is playing.", ephemeral=True)
    vc.pause()
    await interaction.response.send_message("⏸️ Paused.", ephemeral=True)

@bot.tree.command(name="resume", description="Resume playback.")
async def resume(interaction: discord.Interaction):
    vc = interaction.guild.voice_client if interaction.guild else None
    if not vc or not vc.is_paused():
        return await interaction.response.send_message("Nothing to resume.", ephemeral=True)
    vc.resume()
    await interaction.response.send_message("▶️ Resumed.", ephemeral=True)

@bot.tree.command(name="skip", description="Skip current track.")
async def skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client if interaction.guild else None
    if not vc or not (vc.is_playing() or vc.is_paused()):
        return await interaction.response.send_message("Nothing to skip.", ephemeral=True)
    vc.stop()
    await interaction.response.send_message("⏭️ Skipped.")

@bot.tree.command(name="stop", description="Stop and clear the queue.")
async def stop(interaction: discord.Interaction):
    player = bot.get_player(interaction.guild)
    vc = interaction.guild.voice_client if interaction.guild else None
    # Clear queue
    try:
        while True:
            player.queue.get_nowait()
    except asyncio.QueueEmpty:
        pass
    if vc:
        vc.stop()
    await interaction.response.send_message("⏹️ Stopped and cleared the queue.")

@bot.tree.command(name="queue", description="Show the queue.")
async def queue(interaction: discord.Interaction):
    player = bot.get_player(interaction.guild)
    q = player.get_queue_snapshot()
    if not q:
        return await interaction.response.send_message("Queue is empty.", ephemeral=True)
    msg = "\n".join([f"{i+1}. {fmt_track_md(t)}" for i, t in enumerate(q[:20])])
    if len(q) > 20:
        msg += f"\n…and {len(q)-20} more"
    await interaction.response.send_message(msg)

@bot.tree.command(name="np", description="Show what's playing now.")
async def np(interaction: discord.Interaction):
    player = bot.get_player(interaction.guild)
    if not player.current:
        return await interaction.response.send_message("Nothing is playing.", ephemeral=True)
    await interaction.response.send_message(embed=player.make_now_playing_embed())

@bot.tree.command(name="remove", description="Remove an item from the queue by its index (starting at 1).")
@app_commands.describe(index="Index in the queue (1-based)")
async def remove(interaction: discord.Interaction, index: int):
    player = bot.get_player(interaction.guild)
    items = []
    try:
        while True:
            items.append(player.queue.get_nowait())
    except asyncio.QueueEmpty:
        pass
    if 1 <= index <= len(items):
        removed = items.pop(index-1)
        await interaction.response.send_message(f"Removed: {fmt_track_md(removed.data)}")
    else:
        await interaction.response.send_message("Invalid index.", ephemeral=True)
    for it in items:
        player.queue.put_nowait(it)
    await player.announce_now_playing()

@bot.tree.command(name="shuffle", description="Shuffle the queue.")
async def shuffle(interaction: discord.Interaction):
    player = bot.get_player(interaction.guild)
    items = []
    try:
        while True:
            items.append(player.queue.get_nowait())
    except asyncio.QueueEmpty:
        pass
    import random
    random.shuffle(items)
    for it in items:
        player.queue.put_nowait(it)
    await interaction.response.send_message("🔀 Shuffled.")
    await player.announce_now_playing()

@bot.tree.command(name="loop", description="Set loop mode: off, one, all.")
@app_commands.choices(mode=[
    app_commands.Choice(name="off", value=LOOP_OFF),
    app_commands.Choice(name="one", value=LOOP_ONE),
    app_commands.Choice(name="all", value=LOOP_ALL),
])
async def loopmode(interaction: discord.Interaction, mode: app_commands.Choice[str]):
    player = bot.get_player(interaction.guild)
    player.loop_mode = mode.value
    await interaction.response.send_message(f"Loop mode: **{mode.value}**")
    await player.announce_now_playing()

@bot.tree.command(name="autoplay", description="Toggle autoplay.")
@app_commands.choices(state=[
    app_commands.Choice(name="on", value="on"),
    app_commands.Choice(name="off", value="off"),
])
async def autoplay(interaction: discord.Interaction, state: app_commands.Choice[str]):
    player = bot.get_player(interaction.guild)
    player.autoplay = (state.value == "on")
    await interaction.response.send_message(f"Autoplay: **{state.value}**")
    await player.announce_now_playing()

@bot.tree.command(name="volume", description="Set playback volume (0-200%).")
@app_commands.describe(percent="0-200")
async def volume(interaction: discord.Interaction, percent: int):
    if percent < 0 or percent > 200:
        return await interaction.response.send_message("Please provide 0–200.", ephemeral=True)
    player = bot.get_player(interaction.guild)
    player.volume = percent / 100.0
    if player.current:
        player.current.volume = player.volume
    await interaction.response.send_message(f"Volume set to {percent}%.")
    await player.announce_now_playing()

@bot.tree.command(name="seek", description="Seek within the current track (mm:ss or seconds).")
@app_commands.describe(timestamp="e.g., 1:23 or 83")
async def seek(interaction: discord.Interaction, timestamp: str):
    player = bot.get_player(interaction.guild)
    vc = interaction.guild.voice_client if interaction.guild else None
    if not player.current or not vc:
        return await interaction.response.send_message("Nothing is playing.", ephemeral=True)
    secs = parse_time_str(timestamp)
    if secs is None:
        return await interaction.response.send_message("Invalid time format.", ephemeral=True)
    url = player.current.webpage_url
    vc.stop()
    # Replace current with a new source starting at secs
    new_src = await YTDLSource.from_url(url, stream=True, start_time=secs)
    player.current = new_src
    new_src.volume = player.volume
    vc.play(new_src, after=lambda e: player.bot.loop.call_soon_threadsafe(player.next_event.set))
    await interaction.response.send_message(f"⏩ Sought to {human_time(secs)}.")
    await player.announce_now_playing()

@bot.tree.command(name="leave", description="Disconnect from voice.")
async def leave(interaction: discord.Interaction):
    vc = interaction.guild.voice_client if interaction.guild else None
    if vc and vc.is_connected():
        await vc.disconnect(force=True)
        await interaction.response.send_message("Disconnected.")
    else:
        await interaction.response.send_message("I'm not connected.", ephemeral=True)

# ========================== Events ==========================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        await bot.tree.sync()
        print("Slash commands synced.")
    except Exception as e:
        print("Slash sync failed:", e)

# ========================== Entrypoint ==========================

def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Please set DISCORD_TOKEN environment variable.")
    ensure_ffmpeg()
    bot.run(token, log_handler=None)

if __name__ == "__main__":
    main()
