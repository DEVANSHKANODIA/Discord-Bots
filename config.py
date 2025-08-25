"""
Configuration - Bot configuration and settings
"""

import os

# Bot Configuration
BOT_CONFIG = {
    'prefix': '!',  # Fallback prefix for text commands
    'description': 'High-quality Discord music bot with Spotify integration',
    'max_queue_size': 500,
    'max_playlist_size': 100,
    'default_volume': 0.5,
    'command_cooldown': 3,  # seconds
    'max_search_results': 10,
    'autoplay_enabled': True,
    'disconnect_timeout': 300,  # 5 minutes of inactivity
}

# Audio Configuration
AUDIO_CONFIG = {
    'bitrate': 128,  # kbps
    'sample_rate': 48000,  # Hz
    'channels': 2,  # stereo
    'codec': 'opus',
    'reconnect_attempts': 5,
    'reconnect_delay': 5,  # seconds
}

# YT-DLP Configuration
YTDL_CONFIG = {
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
    'source_address': '0.0.0.0',
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'extractor_retries': 3,
    'fragment_retries': 3,
    'skip_unavailable_fragments': True,
}

# FFMPEG Configuration
FFMPEG_CONFIG = {
    'before_options': (
        '-reconnect 1 '
        '-reconnect_streamed 1 '
        '-reconnect_delay_max 5 '
        '-probesize 10M '
        '-analyzeduration 10M'
    ),
    'options': (
        '-vn '
        '-codec:a libopus '
        '-b:a 128k '
        '-ar 48000 '
        '-ac 2 '
        '-application audio '
        '-frame_duration 20 '
        '-packet_loss 1 '
        '-fec 1'
    )
}

# Spotify Configuration
SPOTIFY_CONFIG = {
    'client_id': os.getenv('SPOTIFY_CLIENT_ID', ''),
    'client_secret': os.getenv('SPOTIFY_CLIENT_SECRET', ''),
    'redirect_uri': 'http://localhost:8888/callback',
    'scope': 'playlist-read-private playlist-read-collaborative',
    'market': 'US',  # Default market for track availability
    'max_tracks_per_playlist': 100,
}

# Discord Configuration
DISCORD_CONFIG = {
    'token': os.getenv('DISCORD_TOKEN', ''),
    'command_sync_guilds': None,  # None for global commands, list of guild IDs for specific guilds
    'max_embed_description_length': 4096,
    'max_embed_field_value_length': 1024,
    'max_embed_fields': 25,
    'activity_type': 'listening',
    'activity_name': 'music | /play',
}

# Logging Configuration
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': 'bot.log',
    'max_file_size': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5,
}

# Performance Configuration
PERFORMANCE_CONFIG = {
    'max_concurrent_downloads': 3,
    'download_timeout': 30,  # seconds
    'search_timeout': 10,  # seconds
    'voice_timeout': 10,  # seconds
    'embed_update_interval': 5,  # seconds
    'cleanup_interval': 300,  # 5 minutes
}

# Error Messages
ERROR_MESSAGES = {
    'not_in_voice': "❌ You must be in a voice channel to use music commands!",
    'bot_not_in_voice': "❌ Bot is not connected to a voice channel!",
    'different_voice_channel': "❌ You must be in the same voice channel to control music!",
    'no_track_playing': "❌ Nothing is currently playing!",
    'queue_empty': "❌ Queue is empty!",
    'track_not_found': "❌ Could not find the requested track!",
    'invalid_volume': "❌ Volume must be between 0 and 100!",
    'invalid_url': "❌ Invalid URL provided!",
    'spotify_unavailable': "❌ Spotify integration is not available!",
    'download_failed': "❌ Failed to download track!",
    'connection_failed': "❌ Failed to connect to voice channel!",
    'permission_denied': "❌ You don't have permission to use this command!",
    'rate_limited': "❌ Please wait before using this command again!",
    'queue_full': "❌ Queue is full! Maximum size is {max_size} tracks.",
    'playlist_too_large': "❌ Playlist is too large! Maximum size is {max_size} tracks.",
}

# Success Messages
SUCCESS_MESSAGES = {
    'track_added': "✅ **{title}** has been added to the queue!",
    'playlist_added': "✅ Added {count} tracks from playlist to the queue!",
    'playback_started': "▶️ Now playing **{title}**",
    'playback_paused': "⏸️ Playback paused",
    'playback_resumed': "▶️ Playback resumed",
    'playback_stopped': "⏹️ Playback stopped and queue cleared",
    'track_skipped': "⏭️ Skipped **{title}**",
    'volume_changed': "🔊 Volume set to {volume}%",
    'connected': "🎵 Connected to **{channel}**",
    'disconnected': "👋 Disconnected from voice channel",
    'autoplay_enabled': "🔄 Autoplay enabled",
    'autoplay_disabled': "🔄 Autoplay disabled",
    'queue_shuffled': "🔀 Queue shuffled ({count} tracks)",
}

# Feature Flags
FEATURES = {
    'spotify_integration': True,
    'autoplay': True,
    'queue_persistence': True,
    'voice_reconnect': True,
    'search_suggestions': True,
    'lyrics_support': False,  # Future feature
    'radio_mode': False,  # Future feature
    'equalizer': False,  # Future feature
    'playlist_export': False,  # Future feature
}

# API Endpoints (for future features)
API_ENDPOINTS = {
    'lyrics': 'https://api.lyrics.ovh/v1',
    'lastfm': 'https://ws.audioscrobbler.com/2.0/',
    'musixmatch': 'https://api.musixmatch.com/ws/1.1/',
}

# Regular Expressions
REGEX_PATTERNS = {
    'youtube_url': r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
    'spotify_track': r'spotify\.com\/track\/([a-zA-Z0-9]+)',
    'spotify_playlist': r'spotify\.com\/playlist\/([a-zA-Z0-9]+)',
    'spotify_album': r'spotify\.com\/album\/([a-zA-Z0-9]+)',
    'soundcloud_url': r'soundcloud\.com\/[\w\-\.]+\/[\w\-\.]+',
    'timestamp': r'(?:(\d+):)?(\d+):(\d+)',
}

def get_config_value(section: str, key: str, default=None):
    """Get a configuration value with fallback to default."""
    configs = {
        'bot': BOT_CONFIG,
        'audio': AUDIO_CONFIG,
        'ytdl': YTDL_CONFIG,
        'ffmpeg': FFMPEG_CONFIG,
        'spotify': SPOTIFY_CONFIG,
        'discord': DISCORD_CONFIG,
        'logging': LOGGING_CONFIG,
        'performance': PERFORMANCE_CONFIG,
    }
    
    return configs.get(section, {}).get(key, default)

def update_config_value(section: str, key: str, value):
    """Update a configuration value at runtime."""
    configs = {
        'bot': BOT_CONFIG,
        'audio': AUDIO_CONFIG,
        'spotify': SPOTIFY_CONFIG,
        'discord': DISCORD_CONFIG,
        'performance': PERFORMANCE_CONFIG,
    }
    
    if section in configs and key in configs[section]:
        configs[section][key] = value
        return True
    return False

def validate_config():
    """Validate configuration values and environment variables."""
    errors = []
    warnings = []
    
    # Check required environment variables
    if not DISCORD_CONFIG['token']:
        errors.append("DISCORD_TOKEN environment variable is required!")
    
    # Check Spotify configuration
    if not SPOTIFY_CONFIG['client_id'] or not SPOTIFY_CONFIG['client_secret']:
        warnings.append("Spotify credentials not found. Spotify features will be disabled.")
    
    # Validate numeric ranges
    if not 0 <= BOT_CONFIG['default_volume'] <= 1:
        warnings.append("Invalid default volume, using 0.5")
        BOT_CONFIG['default_volume'] = 0.5
    
    if BOT_CONFIG['max_queue_size'] <= 0:
        warnings.append("Invalid max queue size, using 500")
        BOT_CONFIG['max_queue_size'] = 500
    
    return errors, warnings

# Validate configuration on import
config_errors, config_warnings = validate_config()
if config_errors:
    print("Configuration Errors:")
    for error in config_errors:
        print(f"  - {error}")

if config_warnings:
    print("Configuration Warnings:")
    for warning in config_warnings:
        print(f"  - {warning}")
