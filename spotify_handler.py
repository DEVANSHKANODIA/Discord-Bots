"""
Spotify Integration - Handle Spotify playlist parsing and track extraction
"""

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import logging
import os
import re
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

class SpotifyHandler:
    """Handles Spotify Web API interactions for playlist and track parsing."""
    
    def __init__(self):
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID', '')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET', '')
        self.spotify = None
        
        if self.client_id and self.client_secret:
            try:
                credentials = SpotifyClientCredentials(
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
                self.spotify = spotipy.Spotify(client_credentials_manager=credentials)
                logger.info("Spotify client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Spotify client: {e}")
        else:
            logger.warning("Spotify credentials not found. Spotify features will be disabled.")
    
    def is_spotify_url(self, url: str) -> bool:
        """Check if the URL is a Spotify URL."""
        spotify_patterns = [
            r'https://open\.spotify\.com/',
            r'spotify:',
        ]
        return any(re.search(pattern, url) for pattern in spotify_patterns)
    
    def extract_spotify_id(self, url: str) -> Optional[tuple]:
        """Extract Spotify ID and type (track, playlist, album) from URL."""
        patterns = {
            'track': r'(?:track[/:]([a-zA-Z0-9]+))',
            'playlist': r'(?:playlist[/:]([a-zA-Z0-9]+))',
            'album': r'(?:album[/:]([a-zA-Z0-9]+))'
        }
        
        for content_type, pattern in patterns.items():
            match = re.search(pattern, url)
            if match:
                return content_type, match.group(1)
        
        return None
    
    async def get_track_info(self, track_id: str) -> Optional[Dict]:
        """Get track information from Spotify."""
        if not self.spotify:
            return None
        
        try:
            track = self.spotify.track(track_id)
            return {
                'title': track['name'],
                'artist': ', '.join([artist['name'] for artist in track['artists']]),
                'duration': track['duration_ms'] // 1000,
                'search_query': f"{track['name']} {track['artists'][0]['name']}",
                'thumbnail': track['album']['images'][0]['url'] if track['album']['images'] else None
            }
        except Exception as e:
            logger.error(f"Error getting track info: {e}")
            return None
    
    async def get_playlist_tracks(self, playlist_id: str, limit: int = 50) -> List[Dict]:
        """Get tracks from a Spotify playlist."""
        if not self.spotify:
            return []
        
        tracks = []
        try:
            # Get playlist info
            playlist = self.spotify.playlist(playlist_id)
            logger.info(f"Processing Spotify playlist: {playlist['name']}")
            
            # Get all tracks (handle pagination)
            offset = 0
            while len(tracks) < limit:
                results = self.spotify.playlist_tracks(
                    playlist_id,
                    offset=offset,
                    limit=min(50, limit - len(tracks))
                )
                
                if not results['items']:
                    break
                
                for item in results['items']:
                    if item['track'] and item['track']['type'] == 'track':
                        track = item['track']
                        track_info = {
                            'title': track['name'],
                            'artist': ', '.join([artist['name'] for artist in track['artists']]),
                            'duration': track['duration_ms'] // 1000,
                            'search_query': f"{track['name']} {track['artists'][0]['name']}",
                            'thumbnail': track['album']['images'][0]['url'] if track['album']['images'] else None
                        }
                        tracks.append(track_info)
                
                offset += len(results['items'])
                if not results['next']:
                    break
            
            logger.info(f"Extracted {len(tracks)} tracks from Spotify playlist")
            return tracks
            
        except Exception as e:
            logger.error(f"Error getting playlist tracks: {e}")
            return []
    
    async def get_album_tracks(self, album_id: str) -> List[Dict]:
        """Get tracks from a Spotify album."""
        if not self.spotify:
            return []
        
        tracks = []
        try:
            # Get album info
            album = self.spotify.album(album_id)
            logger.info(f"Processing Spotify album: {album['name']}")
            
            # Get album tracks
            for track in album['tracks']['items']:
                track_info = {
                    'title': track['name'],
                    'artist': ', '.join([artist['name'] for artist in track['artists']]),
                    'duration': track['duration_ms'] // 1000,
                    'search_query': f"{track['name']} {track['artists'][0]['name']}",
                    'thumbnail': album['images'][0]['url'] if album['images'] else None
                }
                tracks.append(track_info)
            
            logger.info(f"Extracted {len(tracks)} tracks from Spotify album")
            return tracks
            
        except Exception as e:
            logger.error(f"Error getting album tracks: {e}")
            return []
    
    async def process_spotify_url(self, url: str, limit: int = 50) -> List[Dict]:
        """Process a Spotify URL and return track information."""
        if not self.spotify:
            logger.error("Spotify client not available")
            return []
        
        spotify_info = self.extract_spotify_id(url)
        if not spotify_info:
            logger.error("Invalid Spotify URL format")
            return []
        
        content_type, content_id = spotify_info
        
        if content_type == 'track':
            track_info = await self.get_track_info(content_id)
            return [track_info] if track_info else []
        
        elif content_type == 'playlist':
            return await self.get_playlist_tracks(content_id, limit)
        
        elif content_type == 'album':
            return await self.get_album_tracks(content_id)
        
        else:
            logger.error(f"Unsupported Spotify content type: {content_type}")
            return []
    
    def search_tracks(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for tracks on Spotify."""
        if not self.spotify:
            return []
        
        try:
            results = self.spotify.search(q=query, type='track', limit=limit)
            tracks = []
            
            for track in results['tracks']['items']:
                track_info = {
                    'title': track['name'],
                    'artist': ', '.join([artist['name'] for artist in track['artists']]),
                    'duration': track['duration_ms'] // 1000,
                    'search_query': f"{track['name']} {track['artists'][0]['name']}",
                    'thumbnail': track['album']['images'][0]['url'] if track['album']['images'] else None
                }
                tracks.append(track_info)
            
            return tracks
            
        except Exception as e:
            logger.error(f"Error searching Spotify tracks: {e}")
            return []
