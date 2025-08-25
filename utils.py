"""
Utility Functions - Helper functions for the music bot
"""

import discord
import math
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def format_duration(seconds: int) -> str:
    """Format duration in seconds to MM:SS or HH:MM:SS format."""
    if seconds <= 0:
        return "00:00"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

def create_progress_bar(current: int, total: int, length: int = 20) -> str:
    """Create a progress bar string."""
    if total <= 0:
        return "▬" * length
    
    filled = int(length * current / total)
    bar = "▰" * filled + "▱" * (length - filled)
    return bar

def create_music_embed(music_player) -> discord.Embed:
    """Create an embed showing current music status."""
    embed = discord.Embed(
        title="🎵 Music Player",
        color=discord.Color.blue()
    )
    
    # Current track info
    if music_player.current_track:
        track = music_player.current_track
        
        # Status
        if music_player.is_paused:
            status = "⏸️ Paused"
            color = discord.Color.orange()
        elif music_player.is_playing:
            status = "▶️ Playing"
            color = discord.Color.green()
        else:
            status = "⏹️ Stopped"
            color = discord.Color.red()
        
        embed.color = color
        embed.title = f"🎵 {status}"
        
        # Track details
        embed.add_field(
            name="Now Playing",
            value=f"**{track.title}**",
            inline=False
        )
        
        if track.duration > 0:
            embed.add_field(
                name="Duration",
                value=format_duration(track.duration),
                inline=True
            )
        
        if track.requester:
            embed.add_field(
                name="Requested by",
                value=track.requester.display_name,
                inline=True
            )
        
        # Volume
        volume_percentage = int(music_player.volume * 100)
        embed.add_field(
            name="Volume",
            value=f"{volume_percentage}%",
            inline=True
        )
        
        # Thumbnail
        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)
    
    else:
        embed.add_field(
            name="Status",
            value="No track currently playing",
            inline=False
        )
    
    # Queue info
    queue_count = len(music_player.queue)
    if queue_count > 0:
        embed.add_field(
            name="Queue",
            value=f"{queue_count} track{'s' if queue_count != 1 else ''} in queue",
            inline=True
        )
    
    # Autoplay status
    autoplay_status = "✅ On" if music_player.autoplay else "❌ Off"
    embed.add_field(
        name="Autoplay",
        value=autoplay_status,
        inline=True
    )
    
    # Voice channel info
    if music_player.voice_client and music_player.voice_client.channel:
        embed.add_field(
            name="Voice Channel",
            value=music_player.voice_client.channel.name,
            inline=True
        )
    
    # Footer
    embed.set_footer(text="Use the buttons below to control playback")
    
    return embed

def create_error_embed(title: str, description: str) -> discord.Embed:
    """Create a standardized error embed."""
    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=discord.Color.red()
    )
    return embed

def create_success_embed(title: str, description: str) -> discord.Embed:
    """Create a standardized success embed."""
    embed = discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=discord.Color.green()
    )
    return embed

def create_info_embed(title: str, description: str) -> discord.Embed:
    """Create a standardized info embed."""
    embed = discord.Embed(
        title=f"ℹ️ {title}",
        description=description,
        color=discord.Color.blue()
    )
    return embed

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to a maximum length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

def is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL."""
    import re
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None

def get_emoji_for_number(number: int) -> str:
    """Get emoji representation for a number (1-10)."""
    emoji_map = {
        1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣",
        6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"
    }
    return emoji_map.get(number, "▶️")

def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing invalid characters."""
    import re
    # Remove invalid characters for filenames
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', ' ', filename)
    # Strip whitespace
    filename = filename.strip()
    # Limit length
    if len(filename) > 100:
        filename = filename[:100]
    
    return filename or "unknown"

def parse_time_string(time_str: str) -> Optional[int]:
    """Parse time string (e.g., '1:30', '2:15:30') to seconds."""
    try:
        parts = time_str.split(':')
        if len(parts) == 2:  # MM:SS
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        elif len(parts) == 3:  # HH:MM:SS
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 1:  # Just seconds
            return int(parts[0])
        else:
            return None
    except ValueError:
        return None

def format_file_size(size_bytes: int) -> str:
    """Format file size in bytes to human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def get_user_permissions(member: discord.Member) -> dict:
    """Get relevant permissions for a member."""
    permissions = member.guild_permissions
    return {
        'administrator': permissions.administrator,
        'manage_guild': permissions.manage_guild,
        'manage_channels': permissions.manage_channels,
        'manage_messages': permissions.manage_messages,
        'connect': permissions.connect,
        'speak': permissions.speak,
        'use_voice_activation': permissions.use_voice_activation
    }

class Logger:
    """Custom logger wrapper with bot-specific formatting."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def info(self, message: str, guild_id: Optional[int] = None):
        """Log info message with optional guild context."""
        if guild_id:
            self.logger.info(f"[Guild {guild_id}] {message}")
        else:
            self.logger.info(message)
    
    def error(self, message: str, guild_id: Optional[int] = None):
        """Log error message with optional guild context."""
        if guild_id:
            self.logger.error(f"[Guild {guild_id}] {message}")
        else:
            self.logger.error(message)
    
    def warning(self, message: str, guild_id: Optional[int] = None):
        """Log warning message with optional guild context."""
        if guild_id:
            self.logger.warning(f"[Guild {guild_id}] {message}")
        else:
            self.logger.warning(message)
    
    def debug(self, message: str, guild_id: Optional[int] = None):
        """Log debug message with optional guild context."""
        if guild_id:
            self.logger.debug(f"[Guild {guild_id}] {message}")
        else:
            self.logger.debug(message)
