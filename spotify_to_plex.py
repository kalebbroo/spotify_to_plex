import csv
import discord
from discord.ext import commands
from plexapi.exceptions import NotFound
from plexapi.server import PlexServer
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from config import (TOKEN, PLEX_TOKEN, BASEURL, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI, ROLE)

# Authenticate with the Plex API
try:
    plex = PlexServer(BASEURL, PLEX_TOKEN)
except Exception as e:
    print(f'Failed to authenticate with the Plex API. Error: {e}')
    quit()

# Authorize with the Spotify API
spotify_auth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET, redirect_uri=SPOTIFY_REDIRECT_URI, scope='playlist-read-private')
try:
    spotify = spotipy.Spotify(auth_manager=spotify_auth)
except Exception as e:
    print(f'Failed to authenticate with the Spotify API. Error: {e}')
    quit()

intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
intents.messages = True
bot = commands.Bot(command_prefix='!')

@bot.slash_command()
@commands.has_role(ROLE)
async def create_playlist(ctx, playlist_url: str, playlist_name: str):
    # Retrieve the selected Spotify playlist
    playlist_id = playlist_url.split('/')[-1]
    try:
        spotify_playlist = spotify.playlist(playlist_id)
    except Exception as e:
        await ctx.send(f'Failed to retrieve the selected Spotify playlist. Error: {e}')
        return

    # Extract the track IDs from the Spotify playlist
    spotify_track_ids = [item['track']['id'] for item in spotify_playlist['tracks']['items']]

    # Retrieve additional information about each track on the selected Spotify playlist
    try:
        spotify_tracks = spotify.tracks(spotify_track_ids)
    except Exception as e:
        await ctx.send(f'Failed to retrieve track information from the Spotify API. Error: {e}')
        return

    # Extract the artist name and song title for each track
    plex_tracks = []
    missing_tracks = []
    for track in spotify_tracks['tracks']:
        artist_name = track['artists'][0]['name']
        song_title = track['name']

        # Search for the track in the Plex library
        try:
            search_results = plex.library.search(artist_name + ' ' + song_title)
        except Exception as e:
            await ctx.send(f'Failed to search for tracks in the Plex library. Error: {e}')
            return

        if search_results:
            plex_tracks.append(search_results[0])
        else:
            missing_tracks.append((artist_name, song_title))

    # Create a new Plex playlist with the available tracks
    try:
        new_playlist = plex.createPlaylist(playlist_name, items=plex_tracks)
    except Exception as e:
        await ctx.send(f'Failed to create a new Plex playlist. Error: {e}')
        return

    # Save the list of missing tracks to a log file
    with open('missing_tracks.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Artist', 'Song Title'])
        writer.writerows(missing_tracks)

    # Send a message back to the user with the results
    response = f'Created a new Plex playlist with {len(plex_tracks)} tracks from the selected Spotify playlist.'
    if missing_tracks:
        response += f' {len(missing_tracks)} tracks were not found in the Plex library. Check the log file for details.'
    await ctx.send(response)

bot.run(TOKEN)  # Replace this with your Discord bot token
