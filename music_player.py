"""
Music Player - Core music functionality
Handles audio streaming, queue management, and voice connections.
"""

import discord
import asyncio
import yt_dlp
import logging
from collections import deque
from typing import Optional, List
import aiohttp
from utils import format_duration, create_music_embed
from music_views import MusicControlView

logger = logging.getLogger(__name__)

class Track:
    """Represents a music track with metadata."""
    
    def __init__(self, title: str, url: str, duration: int = 0, thumbnail: str = None, 
                 requester: discord.Member = None, source_url: str = None):
        self.title = title
        self.url = url
        self.duration = duration
        self.thumbnail = thumbnail
        self.requester = requester
        self.source_url = source_url or url

class MusicPlayer:
    """Handles music playback, queue management, and voice connections."""
    
    def __init__(self, bot, guild):
        self.bot = bot
        self.guild = guild
        self.voice_client: Optional[discord.VoiceClient] = None
        
        # Queue and playback state
        self.queue = deque()
        self.current_track: Optional[Track] = None
        self.is_playing = False
        self.is_paused = False
        self.volume = 0.5
        self.autoplay = True
        
        # Control panel
        self.control_message = None
        self.control_view = None
        
        # YT-DLP options for high-quality audio
        self.ytdl_opts = {
            'format': 'bestaudio/best',
            'extractaudio': True,
            'audioformat': 'opus',
            'noplaylist': True,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch',
            'source_address': '0.0.0.0'
        }
        
        # FFMPEG options for opus codec
        self.ffmpeg_opts = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn -codec:a libopus -b:a 128k -ar 48000'
        }
    
    async def connect_to_voice(self, channel: discord.VoiceChannel) -> bool:
        """Connect to a voice channel."""
        try:
            if self.voice_client and self.voice_client.is_connected():
                if self.voice_client.channel == channel:
                    return True
                await self.voice_client.move_to(channel)
            else:
                # Try to connect with timeout
                self.voice_client = await asyncio.wait_for(
                    channel.connect(timeout=15.0), 
                    timeout=20.0
                )
            
            logger.info(f"Connected to voice channel: {channel.name}")
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"Voice connection timed out for channel: {channel.name}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to voice channel: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from voice channel and cleanup."""
        if self.voice_client:
            await self.voice_client.disconnect()
            self.voice_client = None
        
        self.is_playing = False
        self.is_paused = False
        self.current_track = None
        
        if self.control_view:
            self.control_view.stop()
            self.control_view = None
    
    async def search_track(self, query: str) -> Optional[Track]:
        """Search for a track using yt-dlp."""
        try:
            with yt_dlp.YoutubeDL(self.ytdl_opts) as ytdl:
                # Search for the track
                info = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: ytdl.extract_info(query, download=False)
                )
                
                if 'entries' in info and info['entries']:
                    # Take the first search result
                    entry = info['entries'][0]
                elif 'url' in info:
                    # Direct URL
                    entry = info
                else:
                    return None
                
                track = Track(
                    title=entry.get('title', 'Unknown Title'),
                    url=entry.get('url', ''),
                    duration=entry.get('duration', 0),
                    thumbnail=entry.get('thumbnail', ''),
                    source_url=entry.get('webpage_url', query)
                )
                
                return track
                
        except Exception as e:
            logger.error(f"Error searching for track: {e}")
            return None
    
    async def add_to_queue(self, query: str, requester: discord.Member) -> Optional[Track]:
        """Add a track to the queue."""
        track = await self.search_track(query)
        if track:
            track.requester = requester
            self.queue.append(track)
            logger.info(f"Added to queue: {track.title}")
            return track
        return None
    
    async def play_next(self):
        """Play the next track in the queue."""
        if not self.queue and not self.autoplay:
            self.is_playing = False
            self.current_track = None
            await self.update_control_panel()
            return
        
        if not self.queue and self.autoplay and self.current_track:
            # Try to find related tracks for autoplay
            related_track = await self.get_autoplay_track()
            if related_track:
                self.queue.append(related_track)
        
        if not self.queue:
            self.is_playing = False
            self.current_track = None
            await self.update_control_panel()
            return
        
        track = self.queue.popleft()
        await self.play_track(track)
    
    async def play_track(self, track: Track):
        """Play a specific track."""
        try:
            if not self.voice_client or not self.voice_client.is_connected():
                logger.error("Not connected to voice channel")
                return
            
            # Stop current playback
            if self.voice_client.is_playing():
                self.voice_client.stop()
            
            # Get fresh URL for the track
            fresh_track = await self.search_track(track.source_url)
            if not fresh_track:
                logger.error(f"Failed to get fresh URL for: {track.title}")
                await self.play_next()
                return
            
            # Create audio source
            source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(fresh_track.url, **self.ffmpeg_opts),
                volume=self.volume
            )
            
            # Update current track info
            self.current_track = track
            self.is_playing = True
            self.is_paused = False
            
            # Play the track
            self.voice_client.play(
                source,
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    self._playback_finished(e), self.bot.loop
                )
            )
            
            logger.info(f"Now playing: {track.title}")
            await self.update_control_panel()
            
        except Exception as e:
            logger.error(f"Error playing track: {e}")
            await self.play_next()
    
    async def _playback_finished(self, error):
        """Called when playback finishes."""
        if error:
            logger.error(f"Playback error: {error}")
        
        await self.play_next()
    
    async def pause(self):
        """Pause playback."""
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.pause()
            self.is_paused = True
            await self.update_control_panel()
    
    async def resume(self):
        """Resume playback."""
        if self.voice_client and self.voice_client.is_paused():
            self.voice_client.resume()
            self.is_paused = False
            await self.update_control_panel()
    
    async def stop(self):
        """Stop playback and clear queue."""
        if self.voice_client and (self.voice_client.is_playing() or self.voice_client.is_paused()):
            self.voice_client.stop()
        
        self.queue.clear()
        self.current_track = None
        self.is_playing = False
        self.is_paused = False
        await self.update_control_panel()
    
    async def skip(self):
        """Skip current track."""
        if self.voice_client and (self.voice_client.is_playing() or self.voice_client.is_paused()):
            self.voice_client.stop()
        # play_next will be called automatically by _playback_finished
    
    async def set_volume(self, volume: float):
        """Set playback volume (0.0 to 1.0)."""
        self.volume = max(0.0, min(1.0, volume))
        
        if (self.voice_client and 
            hasattr(self.voice_client.source, 'volume') and 
            isinstance(self.voice_client.source, discord.PCMVolumeTransformer)):
            self.voice_client.source.volume = self.volume
        
        await self.update_control_panel()
    
    async def get_autoplay_track(self) -> Optional[Track]:
        """Get a related track for autoplay (simplified implementation)."""
        if not self.current_track:
            return None
        
        try:
            # Search for similar tracks based on the current track's title
            search_query = f"{self.current_track.title} similar music"
            return await self.search_track(search_query)
        except Exception as e:
            logger.error(f"Error getting autoplay track: {e}")
            return None
    
    async def create_control_panel(self, channel) -> discord.Message:
        """Create the interactive control panel."""
        embed = create_music_embed(self)
        view = MusicControlView(self)
        
        self.control_view = view
        self.control_message = await channel.send(embed=embed, view=view)
        
        return self.control_message
    
    async def update_control_panel(self):
        """Update the control panel with current status."""
        if not self.control_message:
            return
        
        try:
            embed = create_music_embed(self)
            await self.control_message.edit(embed=embed, view=self.control_view)
        except Exception as e:
            logger.error(f"Failed to update control panel: {e}")
    
    async def stop_and_disconnect(self):
        """Stop playback and disconnect from voice."""
        await self.stop()
        await self.disconnect()
    
    async def cleanup(self):
        """Cleanup when bot leaves guild."""
        await self.stop_and_disconnect()
        
        if self.control_view:
            self.control_view.stop()
