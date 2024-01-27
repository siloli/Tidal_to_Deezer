import os
import json
import tidalapi
import subprocess
import deezer
import dotenv
import time
import unicodedata
import sys

# File paths and constants
CREDENTIALS_TIDAL = 'credentials_tidal.json'
CREDENTIALS_DEEZER = 'credentials_deezer.json'
LOG_FILE = 'LogFile.txt'
REMOVE = True  # Remove Tidal playlist after adding it to Deezer


def main(file_namefilter=None):
    try:
        # Load the environment variables and connect to Tidal and Deezer
        dotenv.load_dotenv()
        session = connect_to_tidal()
        client, user = connect_to_deezer()
        # 50 requests each 5s by default to match Deezer API limits
        limiter = RateLimiter(50, 5)

        # Un/comment the following lines to enable/disable the corresponding functions
        get_tidal_tracks_from_playlist(
            session, client, limiter, Playlist_nameFilter=namefilter(file_namefilter) if file_namefilter else namefilter())
        get_tidal_artists(session, client, user, limiter)
        get_tidal_albums(session, client, user, limiter)
        get_tidal_loved_tracks(session, client, user, limiter)
        print("Done!")
    except KeyboardInterrupt as e:
        print(f"Killed by user.")

# RateLimiter class to limit the number of requests made to Deezer API


class RateLimiter:
    def __init__(self, max_requests, period):
        self.max_requests = max_requests
        self.period = period
        self.requests = []

    def wait(self):
        while len(self.requests) >= self.max_requests:
            if time.time() - self.requests[0] > self.period:
                self.requests.pop(0)
            else:
                time.sleep(self.period - (time.time() - self.requests[0]))

    def add_request(self):
        self.wait()
        self.requests.append(time.time())


# Connect to Tidal API
def connect_to_tidal():
    session = tidalapi.Session()
    try:
        if os.path.exists(CREDENTIALS_TIDAL):
            with open(CREDENTIALS_TIDAL, 'r') as file:
                credentials = json.load(file)
                session.load_oauth_session(*credentials.values())
        else:
            raise FileNotFoundError
    except (json.JSONDecodeError, FileNotFoundError):
        print("Corrupted or missing credentials file, connecting normally...")
        session.login_oauth_simple()

        credentials = {
            'token_type': session.token_type,
            'access_token': session.access_token,
            'refresh_token': session.refresh_token,
            'expiry_time': session.expiry_time.isoformat() if session.expiry_time else None
        }

        with open(CREDENTIALS_TIDAL, 'w') as file:
            json.dump(credentials, file)

    print("Successfully connected to Tidal!")
    return session


# Connect to Deezer API
def connect_to_deezer():
    access_token = os.getenv('API_TOKEN')
    if not access_token:
        client, user = get_deezer_credentials()
    else:
        client = deezer.Client(access_token=access_token)
        try:
            user = client.get_user('me')
        except Exception:
            client, user = get_deezer_credentials()

    print("Deezer client initialized with access token.")
    return client, user


# Retrieve Deezer API credentials by using the deezer-oauth command line tool
def get_deezer_credentials():
    print("Error with access token, retrieving new credentials.")
    try:
        if os.path.exists(CREDENTIALS_DEEZER):
            with open(CREDENTIALS_DEEZER, 'r') as file:
                credentials = json.load(file)
                DEEZER_APP_ID = credentials['DEEZER_APP_ID']
                DEEZER_SECRET_TOKEN = credentials['DEEZER_SECRET_TOKEN']

        else:
            raise FileNotFoundError
    except (json.JSONDecodeError, FileNotFoundError):
        print("Missing or corrupted Deezer Application Token")
        exit()

    subprocess.run(["deezer-oauth", DEEZER_APP_ID,
                    DEEZER_SECRET_TOKEN], check=True)
    dotenv.load_dotenv(override=True)
    access_token = os.getenv('API_TOKEN')
    client = deezer.Client(access_token=access_token)
    try:
        user = client.get_user('me')
    except Exception as e:
        print(f"No valid tokens. {e}")
        exit()
    return client, user


# Create a playlist on Deezer
def create_playlist(playlist_name, client, limiter):
    limiter.add_request()
    try:
        deezer_playlist_id = safe_deezer_request(
            client, client, 'create_playlist', limiter, playlist_name)
        print(f"Created playlist: {playlist_name}")
        return deezer_playlist_id
    except Exception as e:
        print(f"Failed to create playlist {playlist_name}: {e}")
        return None


# Search for a track on Deezer
def search_track_on_deezer(track, client, limiter, playlist_name):
    search_results = safe_deezer_request(client, client, 'search', limiter, clean_string(
        f"{track.name} {track.artist.name}"))
    if search_results:
        try:
            return search_results[0].id
        except IndexError:
            pass  # Aucun résultat trouvé, gérer comme ci-dessous
    print(f"No match found for {track.name} by {track.artist.name}")
    log_error('playlist', playlist_name=playlist_name,
              track_name=track.name, artist_name=track.artist.name)
    return None


# Add tracks to a Deezer playlist
def add_tracks_to_deezer_playlist(tracks_id, tidal_playlist, client, limiter):
    deezer_playlist_id = create_playlist(
        tidal_playlist.name, client, limiter)
    deezer_playlist = safe_deezer_request(
        client, client, 'get_playlist', limiter, deezer_playlist_id)
    safe_deezer_request(client, deezer_playlist,
                        'add_tracks', limiter, tracks_id)
    print(
        f"Added {len(tracks_id)} tracks to the playlist {deezer_playlist.title}")

    if REMOVE and isinstance(tidal_playlist, tidalapi.UserPlaylist):
        tidal_playlist.delete()
        print(f"Deleted Tidal playlist: {tidal_playlist.name}")


# Get Tidal tracks from a playlist and add them to Deezer
def get_tidal_tracks_from_playlist(session, client, limiter, Playlist_nameFilter):
    playlists = session.user.playlists()
    for playlist in playlists:
        if Playlist_nameFilter != [] and playlist.name not in Playlist_nameFilter:
            continue

        print(f"Processing playlist: {playlist.name}")
        tracks_id_set = set()
        tracks = playlist.tracks()
        for i, track in enumerate(tracks, 1):
            print(f"{i}/{len(tracks)} {track.name}")
            track_id = search_track_on_deezer(
                track, client, limiter, playlist.name)
            if track_id is not None:
                tracks_id_set.add(track_id)
        if tracks_id_set:
            add_tracks_to_deezer_playlist(
                list(tracks_id_set), playlist, client, limiter)


# Get Tidal artists and add them to Deezer
def get_tidal_artists(session, client, user, limiter):
    tidal_artists = session.user.favorites.artists()
    for i, tidal_artist in enumerate(tidal_artists, 1):
        print(f"{i}/{len(tidal_artists)}. {tidal_artist.name}")
        artist = safe_deezer_request(
            client, client, 'search_artists', limiter, clean_string(tidal_artist.name))
        if artist:
            safe_deezer_request(client, user, 'add_artist', limiter, artist[0])
            print(f"Added {tidal_artist.name} to Deezer")
        else:
            log_error('artist', artist_name=tidal_artist.name)
            print(f"Artist {tidal_artist.name} not found on Deezer")


# Get Tidal albums and add them to Deezer
def get_tidal_albums(session, client, user, limiter):
    tidal_albums = session.user.favorites.albums()
    for i, tidal_album in enumerate(tidal_albums, 1):
        print(f"{i}/{len(tidal_albums)}. {tidal_album.name}")
        limiter.add_request()
        album = safe_deezer_request(client, client, 'search_albums', limiter, clean_string(
            f"{tidal_album.name} {tidal_album.artist.name}"))
        if album:
            safe_deezer_request(client, user, 'add_album', limiter, album[0])
            print(f"Added {tidal_album.name} to Deezer")
        else:
            log_error('album', album_name=tidal_album.name,
                      artist_name=tidal_album.artist.name)
            print(
                f"Album {tidal_album.name} from {tidal_album.artist.name} not found on Deezer")


# Get Tidal loved tracks and add them to Deezer
def get_tidal_loved_tracks(session, client, user, limiter):
    tidal_tracks = session.user.favorites.tracks()
    for _, tidal_track in enumerate(tidal_tracks, 1):
        track = safe_deezer_request(client, client, 'search', limiter, clean_string(
            f"{tidal_track.name} {tidal_track.artist.name}"))
        if track:
            success = False
            try:
                success = safe_deezer_request(
                    client, user, 'add_track', limiter, track[0])
            except deezer.exceptions.DeezerErrorResponse as e:
                if 'code' in e.args[0] and e.args[0]['code'] == 801:
                    print(
                        f"{tidal_track.name} by {tidal_track.artist.name} already added")
            if success:
                print(f"Added {tidal_track.name}")
            else:
                log_error('track', track_name=tidal_track.name,
                          artist_name=tidal_track.artist.name)
                print(
                    f"Track {tidal_track.name} from {tidal_track.artist.name} not found on Deezer")


# Remove all characters that are not letters, numbers, spaces or dots
def clean_string(s):
    return ''.join(c for c in s if unicodedata.category(c)[0] in ('L', 'N'))


# Log errors to a file
def log_error(category, playlist_name=None, artist_name=None, album_name=None, track_name=None):
    with open(LOG_FILE, 'a',  encoding='utf-8') as file:
        match category:
            case "playlist":
                file.write(
                    f"{category}: {playlist_name}, {track_name} by {artist_name}\n")
            case "artist":
                file.write(f"{category}: {artist_name}\n")
            case "album":
                file.write(f"{category}: {album_name} by {artist_name}\n")
            case "track":
                file.write(f"{category}: {track_name} by {artist_name}\n")
            case _:
                file.write(f"unknown error about {category} script\n")


# Make a request to Deezer API and handle OAuthException
def safe_deezer_request(client, obj, method, limiter, *args, **kwargs):
    try:
        # Effectue la requête
        limiter.add_request()
        return getattr(obj, method)(*args, **kwargs)
    except deezer.exceptions.DeezerErrorResponse as e:
        if 'error' in e.args[0] and e.args[0]['error'].get('code') == 801:
            print("Track already exists, skipping...")
            return None
        else:
            print("Access token expired. Renewing...")
            get_deezer_credentials()
            client.access_token = os.getenv('API_TOKEN')
            return getattr(obj, method)(*args, **kwargs)


def namefilter(file='namefilter.txt'):
    try:
        if file is not None and os.path.exists(file):
            with open(file, 'r') as file:
                namefilter = [line.strip() for line in file if line.strip()]
                print(f"Namefilter: {namefilter}")
                return namefilter
        else:
            raise FileNotFoundError
    except (json.JSONDecodeError, FileNotFoundError):
        print("namefilter.txt not found -> no filter")
    return []


# Entry point of the script
if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main()
