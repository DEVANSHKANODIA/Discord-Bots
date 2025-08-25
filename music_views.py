"""
Music Views - Interactive Discord button controls
"""

import discord
from discord.ext import commands
import logging
from utils import format_duration

logger = logging.getLogger(__name__)

class MusicControlView(discord.ui.View):
    """Interactive music control panel with buttons."""
    
    def __init__(self, music_player):
        super().__init__(timeout=None)  # Persistent view
        self.music_player = music_player
    
    @discord.ui.button(
        label="⏯️",
        style=discord.ButtonStyle.primary,
        custom_id="play_pause_button"
    )
    async def play_pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Play/Pause button handler."""
        try:
            # Check if user is in the same voice channel as the bot
            if not self._check_user_voice_access(interaction):
                return await interaction.response.send_message(
                    "❌ You must be in the same voice channel to control music!",
                    ephemeral=True
                )
            
            if self.music_player.is_paused:
                await self.music_player.resume()
                await interaction.response.send_message("▶️ Resumed playback", ephemeral=True)
            elif self.music_player.is_playing:
                await self.music_player.pause()
                await interaction.response.send_message("⏸️ Paused playback", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Nothing to play/pause!", ephemeral=True)
        
        except Exception as e:
            logger.error(f"Error in play/pause button: {e}")
            await interaction.response.send_message("❌ An error occurred", ephemeral=True)
    
    @discord.ui.button(
        label="⏭️",
        style=discord.ButtonStyle.secondary,
        custom_id="skip_button"
    )
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Skip button handler."""
        try:
            if not self._check_user_voice_access(interaction):
                return await interaction.response.send_message(
                    "❌ You must be in the same voice channel to control music!",
                    ephemeral=True
                )
            
            if not self.music_player.current_track:
                return await interaction.response.send_message(
                    "❌ Nothing is currently playing!",
                    ephemeral=True
                )
            
            skipped_track = self.music_player.current_track.title
            await self.music_player.skip()
            await interaction.response.send_message(
                f"⏭️ Skipped **{skipped_track}**",
                ephemeral=True
            )
        
        except Exception as e:
            logger.error(f"Error in skip button: {e}")
            await interaction.response.send_message("❌ An error occurred", ephemeral=True)
    
    @discord.ui.button(
        label="⏹️",
        style=discord.ButtonStyle.danger,
        custom_id="stop_button"
    )
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Stop button handler."""
        try:
            if not self._check_user_voice_access(interaction):
                return await interaction.response.send_message(
                    "❌ You must be in the same voice channel to control music!",
                    ephemeral=True
                )
            
            await self.music_player.stop()
            await interaction.response.send_message("⏹️ Stopped playback and cleared queue", ephemeral=True)
        
        except Exception as e:
            logger.error(f"Error in stop button: {e}")
            await interaction.response.send_message("❌ An error occurred", ephemeral=True)
    
    @discord.ui.button(
        label="📋",
        style=discord.ButtonStyle.secondary,
        custom_id="queue_button"
    )
    async def queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Queue display button handler."""
        try:
            embed = discord.Embed(
                title="📋 Music Queue",
                color=discord.Color.blue()
            )
            
            # Current track
            if self.music_player.current_track:
                status = "⏸️ Paused" if self.music_player.is_paused else "▶️ Playing"
                embed.add_field(
                    name="Now Playing",
                    value=f"{status} **{self.music_player.current_track.title}**",
                    inline=False
                )
            
            # Queue
            if self.music_player.queue:
                queue_text = ""
                for i, track in enumerate(list(self.music_player.queue)[:10]):
                    queue_text += f"{i+1}. **{track.title}**\n"
                
                if len(self.music_player.queue) > 10:
                    queue_text += f"\n... and {len(self.music_player.queue) - 10} more tracks"
                
                embed.add_field(
                    name=f"Up Next ({len(self.music_player.queue)} tracks)",
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
        
        except Exception as e:
            logger.error(f"Error in queue button: {e}")
            await interaction.response.send_message("❌ An error occurred", ephemeral=True)
    
    @discord.ui.button(
        label="🔄",
        style=discord.ButtonStyle.secondary,
        custom_id="autoplay_button"
    )
    async def autoplay_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Autoplay toggle button handler."""
        try:
            if not self._check_user_voice_access(interaction):
                return await interaction.response.send_message(
                    "❌ You must be in the same voice channel to control music!",
                    ephemeral=True
                )
            
            self.music_player.autoplay = not self.music_player.autoplay
            status = "enabled" if self.music_player.autoplay else "disabled"
            
            await interaction.response.send_message(
                f"🔄 Autoplay has been {status}",
                ephemeral=True
            )
            
            # Update the control panel to reflect the change
            await self.music_player.update_control_panel()
        
        except Exception as e:
            logger.error(f"Error in autoplay button: {e}")
            await interaction.response.send_message("❌ An error occurred", ephemeral=True)
    
    def _check_user_voice_access(self, interaction: discord.Interaction) -> bool:
        """Check if user has permission to control music (in same voice channel)."""
        if not hasattr(interaction.user, 'voice') or not interaction.user.voice:
            return False
        
        if not self.music_player.voice_client:
            return True  # Bot not in voice, allow control
        
        return interaction.user.voice.channel == self.music_player.voice_client.channel

class VolumeControlModal(discord.ui.Modal, title="Volume Control"):
    """Modal for volume control input."""
    
    def __init__(self, music_player):
        super().__init__()
        self.music_player = music_player
    
    volume = discord.ui.TextInput(
        label="Volume",
        placeholder="Enter volume (0-100)...",
        min_length=1,
        max_length=3,
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle volume modal submission."""
        try:
            volume_value = int(self.volume.value)
            if not 0 <= volume_value <= 100:
                return await interaction.response.send_message(
                    "❌ Volume must be between 0 and 100!",
                    ephemeral=True
                )
            
            await self.music_player.set_volume(volume_value / 100.0)
            await interaction.response.send_message(
                f"🔊 Volume set to {volume_value}%",
                ephemeral=True
            )
        
        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter a valid number!",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in volume modal: {e}")
            await interaction.response.send_message(
                "❌ An error occurred",
                ephemeral=True
            )

class ExtendedMusicControlView(MusicControlView):
    """Extended music control panel with additional features."""
    
    def __init__(self, music_player):
        super().__init__(music_player)
    
    @discord.ui.button(
        label="🔊",
        style=discord.ButtonStyle.secondary,
        custom_id="volume_button",
        row=1
    )
    async def volume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Volume control button handler."""
        try:
            if not self._check_user_voice_access(interaction):
                return await interaction.response.send_message(
                    "❌ You must be in the same voice channel to control music!",
                    ephemeral=True
                )
            
            modal = VolumeControlModal(self.music_player)
            await interaction.response.send_modal(modal)
        
        except Exception as e:
            logger.error(f"Error in volume button: {e}")
            await interaction.response.send_message("❌ An error occurred", ephemeral=True)
    
    @discord.ui.button(
        label="🔀",
        style=discord.ButtonStyle.secondary,
        custom_id="shuffle_button",
        row=1
    )
    async def shuffle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Shuffle queue button handler."""
        try:
            if not self._check_user_voice_access(interaction):
                return await interaction.response.send_message(
                    "❌ You must be in the same voice channel to control music!",
                    ephemeral=True
                )
            
            if not self.music_player.queue:
                return await interaction.response.send_message(
                    "❌ Queue is empty!",
                    ephemeral=True
                )
            
            # Shuffle the queue
            import random
            queue_list = list(self.music_player.queue)
            random.shuffle(queue_list)
            self.music_player.queue.clear()
            self.music_player.queue.extend(queue_list)
            
            await interaction.response.send_message(
                f"🔀 Shuffled {len(queue_list)} tracks in the queue",
                ephemeral=True
            )
        
        except Exception as e:
            logger.error(f"Error in shuffle button: {e}")
            await interaction.response.send_message("❌ An error occurred", ephemeral=True)
    
    @discord.ui.button(
        label="👋",
        style=discord.ButtonStyle.danger,
        custom_id="disconnect_button",
        row=1
    )
    async def disconnect_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Disconnect button handler."""
        try:
            if not self._check_user_voice_access(interaction):
                return await interaction.response.send_message(
                    "❌ You must be in the same voice channel to control music!",
                    ephemeral=True
                )
            
            await self.music_player.stop_and_disconnect()
            await interaction.response.send_message("👋 Disconnected from voice channel", ephemeral=True)
            
            # Stop the view since bot is disconnected
            self.stop()
        
        except Exception as e:
            logger.error(f"Error in disconnect button: {e}")
            await interaction.response.send_message("❌ An error occurred", ephemeral=True)
