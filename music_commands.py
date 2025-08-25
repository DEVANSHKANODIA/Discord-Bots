"""
Music Commands - Discord slash commands for music control
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
from spotify_handler import SpotifyHandler
from utils import create_music_embed

logger = logging.getLogger(__name__)

class MusicCommands(commands.Cog):
    """Discord slash commands for music functionality."""
    
    def __init__(self, bot):
        self.bot = bot
        self.spotify = SpotifyHandler()
    
    async def cog_load(self):
        """Called when the cog is loaded."""
        logger.info("Music commands cog loaded")
    
    def get_music_player(self, guild_id):
        """Get the music player for a guild."""
        return self.bot.get_music_player(guild_id)
    
    @app_commands.command(name="play", description="Play music from YouTube or Spotify")
    @app_commands.describe(query="Song name, YouTube URL, or Spotify URL")
    async def play(self, interaction: discord.Interaction, query: str):
        """Play music command."""
        # Check if user is in a voice channel first (before defer)
        if not hasattr(interaction.user, 'voice') or not interaction.user.voice:
            embed = discord.Embed(
                title="❌ Error",
                description="You must be in a voice channel to use music commands!",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Now defer after initial checks
        await interaction.response.defer()
        
        voice_channel = interaction.user.voice.channel
        music_player = self.get_music_player(interaction.guild_id)
        
        if not music_player:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to initialize music player!",
                color=discord.Color.red()
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Connect to voice channel
        if not await music_player.connect_to_voice(voice_channel):
            embed = discord.Embed(
                title="❌ Voice Connection Failed",
                description=(
                    "Unable to connect to the voice channel. This may be due to:\n"
                    "• Network/firewall restrictions in hosted environments\n"
                    "• Missing bot permissions\n"
                    "• Voice channel is full or restricted\n\n"
                    "💡 **Tip**: Try running the bot on your local computer for full voice support."
                ),
                color=discord.Color.red()
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Handle Spotify URLs
        if self.spotify.is_spotify_url(query):
            tracks = await self.spotify.process_spotify_url(query, limit=100)
            if not tracks:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to process Spotify URL or no tracks found!",
                    color=discord.Color.red()
                )
                return await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Add tracks to queue
            added_count = 0
            for track_info in tracks[:50]:  # Limit to 50 tracks to prevent spam
                track = await music_player.add_to_queue(
                    track_info['search_query'],
                    interaction.user
                )
                if track:
                    added_count += 1
            
            embed = discord.Embed(
                title="📋 Playlist Added",
                description=f"Added {added_count} tracks from Spotify to the queue!",
                color=discord.Color.green()
            )
            
            # Start playing if not already playing
            if not music_player.is_playing and not music_player.current_track:
                await music_player.play_next()
            
        else:
            # Handle regular YouTube search/URL
            track = await music_player.add_to_queue(query, interaction.user)
            if not track:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Could not find or add the requested track!",
                    color=discord.Color.red()
                )
                return await interaction.followup.send(embed=embed, ephemeral=True)
            
            embed = discord.Embed(
                title="✅ Track Added",
                description=f"**{track.title}** has been added to the queue!",
                color=discord.Color.green()
            )
            
            if track.thumbnail:
                embed.set_thumbnail(url=track.thumbnail)
            
            # Start playing if not already playing
            if not music_player.is_playing and not music_player.current_track:
                await music_player.play_next()
        
        await interaction.followup.send(embed=embed)
        
        # Create or update control panel
        if not music_player.control_message:
            await music_player.create_control_panel(interaction.channel)
    
    @app_commands.command(name="pause", description="Pause the current track")
    async def pause(self, interaction: discord.Interaction):
        """Pause playback."""
        music_player = self.get_music_player(interaction.guild_id)
        
        if not music_player or not music_player.is_playing:
            embed = discord.Embed(
                title="❌ Error",
                description="Nothing is currently playing!",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        await music_player.pause()
        
        embed = discord.Embed(
            title="⏸️ Paused",
            description="Playback has been paused.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="resume", description="Resume the current track")
    async def resume(self, interaction: discord.Interaction):
        """Resume playback."""
        music_player = self.get_music_player(interaction.guild_id)
        
        if not music_player or not music_player.is_paused:
            embed = discord.Embed(
                title="❌ Error",
                description="Nothing is currently paused!",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        await music_player.resume()
        
        embed = discord.Embed(
            title="▶️ Resumed",
            description="Playback has been resumed.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="skip", description="Skip the current track")
    async def skip(self, interaction: discord.Interaction):
        """Skip current track."""
        music_player = self.get_music_player(interaction.guild_id)
        
        if not music_player or not music_player.current_track:
            embed = discord.Embed(
                title="❌ Error",
                description="Nothing is currently playing!",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        skipped_track = music_player.current_track.title
        await music_player.skip()
        
        embed = discord.Embed(
            title="⏭️ Skipped",
            description=f"Skipped **{skipped_track}**",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="stop", description="Stop playback and clear the queue")
    async def stop(self, interaction: discord.Interaction):
        """Stop playback and clear queue."""
        music_player = self.get_music_player(interaction.guild_id)
        
        if not music_player:
            embed = discord.Embed(
                title="❌ Error",
                description="No music player found!",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        await music_player.stop()
        
        embed = discord.Embed(
            title="⏹️ Stopped",
            description="Playback stopped and queue cleared.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="queue", description="Show the current music queue")
    async def queue(self, interaction: discord.Interaction):
        """Display the current queue."""
        music_player = self.get_music_player(interaction.guild_id)
        
        if not music_player:
            embed = discord.Embed(
                title="❌ Error",
                description="No music player found!",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        embed = discord.Embed(
            title="📋 Music Queue",
            color=discord.Color.blue()
        )
        
        # Current track
        if music_player.current_track:
            status = "⏸️ Paused" if music_player.is_paused else "▶️ Playing"
            embed.add_field(
                name="Now Playing",
                value=f"{status} **{music_player.current_track.title}**",
                inline=False
            )
        
        # Queue
        if music_player.queue:
            queue_text = ""
            for i, track in enumerate(list(music_player.queue)[:10]):  # Show first 10
                queue_text += f"{i+1}. **{track.title}**\n"
            
            if len(music_player.queue) > 10:
                queue_text += f"\n... and {len(music_player.queue) - 10} more tracks"
            
            embed.add_field(
                name=f"Up Next ({len(music_player.queue)} tracks)",
                value=queue_text,
                inline=False
            )
        else:
            embed.add_field(
                name="Up Next",
                value="Queue is empty",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="volume", description="Set playback volume (0-100)")
    @app_commands.describe(volume="Volume level (0-100)")
    async def volume(self, interaction: discord.Interaction, volume: int):
        """Set playback volume."""
        if not 0 <= volume <= 100:
            embed = discord.Embed(
                title="❌ Error",
                description="Volume must be between 0 and 100!",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        music_player = self.get_music_player(interaction.guild_id)
        
        if not music_player:
            embed = discord.Embed(
                title="❌ Error",
                description="No music player found!",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        await music_player.set_volume(volume / 100.0)
        
        embed = discord.Embed(
            title="🔊 Volume",
            description=f"Volume set to {volume}%",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="disconnect", description="Disconnect the bot from voice channel")
    async def disconnect(self, interaction: discord.Interaction):
        """Disconnect from voice channel."""
        music_player = self.get_music_player(interaction.guild_id)
        
        if not music_player or not music_player.voice_client:
            embed = discord.Embed(
                title="❌ Error",
                description="Bot is not connected to a voice channel!",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        await music_player.stop_and_disconnect()
        
        embed = discord.Embed(
            title="👋 Disconnected",
            description="Disconnected from voice channel.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="autoplay", description="Toggle autoplay mode")
    async def autoplay(self, interaction: discord.Interaction):
        """Toggle autoplay functionality."""
        music_player = self.get_music_player(interaction.guild_id)
        
        if not music_player:
            embed = discord.Embed(
                title="❌ Error",
                description="No music player found!",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        music_player.autoplay = not music_player.autoplay
        status = "enabled" if music_player.autoplay else "disabled"
        
        embed = discord.Embed(
            title="🔄 Autoplay",
            description=f"Autoplay has been {status}.",
            color=discord.Color.green() if music_player.autoplay else discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
