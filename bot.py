"""
Discord Music Bot - Main Bot Class
Handles bot initialization, events, and command registration.
"""

import discord
from discord.ext import commands
import logging
from music_player import MusicPlayer
from music_commands import MusicCommands
from config import BOT_CONFIG

logger = logging.getLogger(__name__)

class MusicBot(commands.Bot):
    """Main Discord music bot class with slash commands and interactive components."""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.guilds = True
        
        super().__init__(
            command_prefix=BOT_CONFIG['prefix'],
            intents=intents,
            description="High-quality Discord music bot with Spotify integration"
        )
        
        # Initialize music players for each guild
        self.music_players = {}
        
    async def setup_hook(self):
        """Called when the bot is starting up."""
        logger.info("Setting up bot...")
        
        # Add music commands cog
        await self.add_cog(MusicCommands(self))
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    async def on_ready(self):
        """Called when the bot is ready and connected to Discord."""
        logger.info(f"{self.user} has connected to Discord!")
        logger.info(f"Bot is in {len(self.guilds)} guild(s)")
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.listening,
            name="music | /play"
        )
        await self.change_presence(activity=activity)
    
    async def on_guild_join(self, guild):
        """Called when the bot joins a new guild."""
        logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")
        
        # Initialize music player for the new guild
        self.music_players[guild.id] = MusicPlayer(self, guild)
    
    async def on_guild_remove(self, guild):
        """Called when the bot leaves a guild."""
        logger.info(f"Left guild: {guild.name} (ID: {guild.id})")
        
        # Clean up music player
        if guild.id in self.music_players:
            await self.music_players[guild.id].cleanup()
            del self.music_players[guild.id]
    
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state updates for bot disconnect logic."""
        if member == self.user:
            return
        
        # If the bot is alone in a voice channel, disconnect after a delay
        voice_client = discord.utils.get(self.voice_clients, guild=member.guild)
        if voice_client and voice_client.channel:
            # Check if bot is alone (only the bot in the channel)
            if len([m for m in voice_client.channel.members if not m.bot]) == 0:
                logger.info(f"Bot is alone in voice channel, disconnecting...")
                if member.guild.id in self.music_players:
                    await self.music_players[member.guild.id].stop_and_disconnect()
    
    def get_music_player(self, guild_id):
        """Get or create a music player for a guild."""
        if guild_id not in self.music_players:
            guild = self.get_guild(guild_id)
            if guild:
                self.music_players[guild_id] = MusicPlayer(self, guild)
        
        return self.music_players.get(guild_id)
    
    async def on_command_error(self, ctx, error):
        """Global error handler for commands."""
        if isinstance(error, commands.CommandNotFound):
            return
        
        logger.error(f"Command error in {ctx.command}: {error}")
        
        embed = discord.Embed(
            title="❌ Error",
            description=f"An error occurred: {str(error)}",
            color=discord.Color.red()
        )
        
        try:
            await ctx.respond(embed=embed, ephemeral=True)
        except:
            try:
                await ctx.send(embed=embed)
            except:
                logger.error("Failed to send error message to user")
