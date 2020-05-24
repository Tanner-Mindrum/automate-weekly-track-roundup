from __future__ import print_function
import requests
import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import json
from urllib.parse import urlparse, parse_qs
from googleapiclient.errors import HttpError
from secrets import tm_secret, spot_user_id, tm_spotify_id, tm_spotify_secret, spot_username, spot_redirect_uri,\
    automatewtr_secret, tm_web_secret
import pickle
import os.path
from google.auth.transport.requests import Request
import datetime
import spotipy as spotipy

scopes = ["https://www.googleapis.com/auth/youtube"]

def main():
    print("Getting this week's latest in music, as reviewed by theneedledrop!\n"
          "------------------------------------------------------------------")

    # spotify credentials
    spotify_client_id = tm_spotify_id
    spotify_client_secret = tm_spotify_secret
    spotify_user_id = spot_user_id
    spotify_username = spot_username
    spotify_redirect_uri = spot_redirect_uri

    '''Authorize Spotify user account '''
    spotify_token = spotipy.prompt_for_user_token(
        spotify_username,
        'user-read-private,playlist-read-private,playlist-modify-private,playlist-modify,playlist-modify-public',
        client_id=spotify_client_id,
        client_secret=spotify_client_secret,
        redirect_uri=spotify_redirect_uri
    )

    # youtube credentials
    api_service_name = "youtube"
    api_version = "v3"
    client_secrets_file = tm_web_secret

    ''' Authorize Youtube account once and store credentials with pickle '''
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # if there are no valid credentials, provide the user with log in popup
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
            creds = flow.run_console()
        # save the credentials for subsequent runs
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    # create a youtube client
    youtube = googleapiclient.discovery.build(api_service_name, api_version, credentials=creds)

    ''' Get the most recent weekly track roundup video '''
    # collect recent weekly track roundup videos
    request = youtube.playlistItems().list(
        part="snippet",
        playlistId="PLP4CSgl7K7or84AAhr7zlLNpghEnKWu2c",
        maxResults=2
    )
    response = request.execute()
    # find the most recent video and get its details
    recent_roundup_obj = ""
    for (k, v) in response.items():
        if k == "items":
            recent_roundup_obj = v[0]
            break

    # get the title, description, and parsed date from the most recent video
    title = ""
    description = ""
    for (k, v) in recent_roundup_obj.items():
        if k == "snippet":
            snip_obj = json.loads(json.dumps(v))
            description = json.loads(json.dumps(snip_obj['description']))
            title = json.loads(json.dumps(snip_obj['title']))
            break
    date = title[22:26] + '/' + str(datetime.datetime.now().year)

    ''' Get last week's old Spotify playlists and unfollow them '''
    # This is to make sure our list of playlists doesn't get cluttered. By now, i should've listened to last week's
    # songs already.
    query = "https://api.spotify.com/v1/users/{}/playlists".format(spotify_user_id)
    request = requests.get(
        query,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(spotify_token)
        }
    )
    response = request.json()
    items = response["items"]
    playlist_names = ["Best tracks of the week", "Meh tracks of the week", "Worst tracks of the week"]
    playlists_ids_to_unfollow = []
    for item in items:
        playlist_name = item["name"]
        playlist_date = playlist_name[playlist_name.find(":") + 2:]
        playlist_name = playlist_name[:playlist_name.find(":")]
        if playlist_name in playlist_names and playlist_date != date:
            playlists_ids_to_unfollow.append(item["id"])

    count = 0
    length = len(playlists_ids_to_unfollow)
    for playlist_id in range(length):
        query = "https://api.spotify.com/v1/playlists/{}/followers".format(playlists_ids_to_unfollow[count])
        requests.delete(
            query,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        count += 1

    ''' Get last week's old Youtube playlists and unfollow them '''
    request = youtube.playlists().list(
        part="snippet,contentDetails",
        maxResults=15,
        mine=True
    )
    response = request.execute()
    items = response["items"]
    playlist_names = ["Best tracks of the week", "Meh tracks of the week", "Worst tracks of the week"]
    playlists_ids_to_unfollow = []
    for item in items:
        playlist_name = item["snippet"]["title"]
        playlist_date = playlist_name[playlist_name.find(":") + 2:]
        playlist_name = playlist_name[:playlist_name.find(":")]
        if playlist_name in playlist_names and playlist_date != date:
            playlists_ids_to_unfollow.append(item["id"])

    count = 0
    length = len(playlists_ids_to_unfollow)
    for playlist_id in range(length):
        request = youtube.playlists().delete(id=playlists_ids_to_unfollow[count])
        request.execute()
        count += 1

    ''' Create a "best"/"meh"/"worst" tracks of the week playlist on Youtube '''
    # best_playlist_id = create_best_playlist(youtube, date)
    # meh_playlist_id = create_meh_playlist(youtube, date)
    # worst_playlist_id = create_worst_playlist(youtube, date)

    ''' Create a "best"/"meh"/"worst" tracks of the week playlist on Spotify '''
    playlist_ids = create_spotify_playlists(spotify_user_id, spotify_token, date)

    id_enum = 0  # best: 1, meh: 2, worst: 3
    for line in description.splitlines():
        if "best tracks" in line.lower():
            id_enum = 1
            continue
        elif "meh" in line.lower():
            id_enum = 2
            continue
        elif "worst tracks" in line.lower():
            id_enum = 3
            continue
        try:
            extracted_id = str(get_yt_video_id(line)).strip(' ')
            if extracted_id is not None and 1 <= id_enum <= 3:  # found a video and it's in a best/meh/worst section
                # search up the video for its key attributes
                request = youtube.videos().list(
                    part="snippet,contentDetails,statistics",
                    id=extracted_id
                )
                request.execute()

                # if id_enum == 1:
                #     add_to_youtube_playlist(youtube, best_playlist_id, extracted_id)
                # elif id_enum == 2:
                #     add_to_youtube_playlist(youtube, meh_playlist_id, extracted_id)
                # elif id_enum == 3:
                #     add_to_youtube_playlist(youtube, worst_playlist_id, extracted_id)

        except ValueError:
            if " - " in line.lower():
                og_song_name = line[line.find("-") + 2:]
                if "(" in line.lower():
                    line = line[:line.find("(") - 1]
                if "ft" in line.lower():
                    line = line[:line.find("ft") - 1]
                if "*" in line.lower():
                    line = line[:line.find("*") - 1]
                artist = line[:line.find("-") - 1]
                song_name = line[line.find("-") + 2:]
                if "&" in song_name:
                    song_name = ''.join(c if c != '&' else 'and' for c in song_name)
                song_uri = get_spotify_uri(spotify_token, song_name, artist, og_song_name)
                if id_enum == 1:
                    add_song_to_spotify_playlist(playlist_ids[0], song_uri, spotify_token)
                elif id_enum == 2:
                    add_song_to_spotify_playlist(playlist_ids[1], song_uri, spotify_token)
                elif id_enum == 3:
                    add_song_to_spotify_playlist(playlist_ids[2], song_uri, spotify_token)

            continue

    print("Playlists created!\nLog in to Spotify to view your playlists!\nAlso, visit "
          "https://www.youtube.com/feed/library to view your playlists on Youtube.")


def create_spotify_playlists(spotify_user_id, spotify_token, date):
    playlist_title_types = ["Best tracks of the week: " + date, "Meh tracks of the week: " + date,
                            "Worst tracks of the week: " + date]
    playlist_types = ["best", "meh", "worst"]
    playlist_ids = []
    for playlist in range(3):
        playlist_description = "This playlist contains the {} songs from theneedledrop's Weekly Track Roundup on {}" \
            .format(playlist_types[playlist], date)

        request_body = json.dumps({
            "name": playlist_title_types[playlist],
            "description": playlist_description,
            "public": True
        })
        query = "https://api.spotify.com/v1/users/{}/playlists".format(spotify_user_id)
        request = requests.post(
            query,
            data=request_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        id = request.json()["id"]
        playlist_ids.append(id)
    return playlist_ids


def get_spotify_uri(spotify_token, song_name, artist, og_song_name):
    ''' Search for a song '''
    try:
        query = "https://api.spotify.com/v1/search?query=+track:{}+artist:{}&type=track&offset=0&limit=20".format(
            song_name,
            artist
        )
        request = requests.get(
            query,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response = request.json()
        songs = response["tracks"]["items"]

        current_best = ""
        count = 0
        og_song_name = ''.join(e for e in og_song_name if e.isalnum())
        for song in songs:
            curr_song = ''.join(e for e in song["name"] if e.isalnum())
            if curr_song == og_song_name:
                return songs[count]["uri"]
            elif curr_song == song_name:
                current_best = song["uri"]
            count += 1

        if current_best == "":
            return songs[0]["uri"]

        return current_best
    except IndexError:
        return


def add_song_to_spotify_playlist(playlist_id, song_uri, spotify_token):
    query = "https://api.spotify.com/v1/playlists/{}/tracks?uris={}".format(playlist_id, song_uri)
    request = requests.post(
        query,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(spotify_token)
        }
    )
    request.json()

def create_best_playlist(youtube, time):
    request = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": "Best tracks of the week: " + time,
                "description": "Best tracks from theneedledrop's Weekly Track Roundup on " + time +
                               ".\n\nAutomated using YouTube API.",
                "tags": [
                    "weekly track roundup"
                    "best tracks",
                    "created with youtube api"
                ],
                "defaultLanguage": "en"
            },
            "status": {
                "privacyStatus": "private"
            }
        }
    )
    response = request.execute()
    return json.loads(json.dumps(response['id']))


def create_meh_playlist(youtube, time):
    request = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": "Meh tracks of the week: " + time,
                "description": "Meh tracks from theneedledrop's Weekly Track Roundup on " + time +
                               ".\n\nAutomated using YouTube API.",
                "tags": [
                    "weekly track roundup"
                    "meh tracks",
                    "created with youtube api"
                ],
                "defaultLanguage": "en"
            },
            "status": {
                "privacyStatus": "private"
            }
        }
    )
    response = request.execute()
    return json.loads(json.dumps(response['id']))


def create_worst_playlist(youtube, time):
    request = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": "Worst tracks of the week: " + time,
                "description": "Worst tracks from theneedledrop's Weekly Track Roundup on " + time +
                               ".\n\nAutomated using YouTube API.",
                "tags": [
                    "weekly track roundup"
                    "worst tracks",
                    "created with youtube api"
                ],
                "defaultLanguage": "en"
            },
            "status": {
                "privacyStatus": "private"
            }
        }
    )
    response = request.execute()
    return json.loads(json.dumps(response['id']))


def add_to_youtube_playlist(youtube, playlist_id, vid_id):
    try:
        request = youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "position": 0,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": vid_id
                    }
                }
            }
        )
        request.execute()
    except requests.exceptions.HTTPError and HttpError:
        return


''' returns a valid id extracted from a youtube url '''
def get_yt_video_id(url):
    if url.startswith(('youtu', 'www')):
        url = 'http://' + url

    query = urlparse(url)

    if query.hostname is not None and 'youtube' in query.hostname:
        if query.path == '/watch':
            return parse_qs(query.query)['v'][0]
        elif query.path.startswith(('/embed/', '/v/')):
            return query.path.split('/')[2]
    elif query.hostname is not None and 'youtu.be' in query.hostname:
        return query.path[1:]
    else:
        raise ValueError


if __name__ == "__main__":
    main()
