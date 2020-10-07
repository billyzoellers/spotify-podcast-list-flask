"""
  Simple app to list episodes of a show on Spotify and their watch status
    Author: Billy Zoellers
"""
import os
import time
import spotipy
import spotipy.util as util
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = 'super secret key'

## App params
CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SEC = os.getenv("SPOTIPY_CLIENT_SECRET")
APP_URI = os.getenv("APP_URI")
API_BASE = 'https://accounts.spotify.com'
REDIRECT_URI = f'{APP_URI}/callback'
SCOPE = 'user-library-read,user-read-playback-position'
SHOW_DIALOG = False
PAGE_SIZE = 50

@app.route("/")
def index():
  session['token_info'], authorized = get_token(session)
  session.modified = True
  if not authorized:
    return redirect('verify')
  
  sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))
  offset = 0
  shows = []
  while True:
    page = sp.current_user_saved_shows(limit=PAGE_SIZE, offset=offset)
    shows = shows + page['items']
    offset += PAGE_SIZE
    if page['next'] is None:
      break
  return render_template('index.html', shows=shows)

@app.route("/show/<showId>")
def show(showId):
  session['token_info'], authorized = get_token(session)
  session.modified = True
  if not authorized:
    return redirect('verify')
  
  sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))

  offset = 0
  episodes = []
  while True:
    page = sp.show_episodes(showId, limit=PAGE_SIZE, offset=offset)
    episodes = episodes + page['items']
    offset += PAGE_SIZE
    if page['next'] is None:
      break

  ## Add some friendly values to each episodes
  ms_per_minute = 60000
  for episode in episodes:
    episode['resume_point_min'] = round(episode['resume_point']['resume_position_ms'] / ms_per_minute)
    episode['duration_min'] = round(episode['duration_ms'] / ms_per_minute)

  return render_template("show.html", episodes=episodes)

## Spotify OAuth flow
@app.route("/verify")
def verify():
  sp_oauth = spotipy.oauth2.SpotifyOAuth(
    client_id = CLIENT_ID,
    client_secret = CLIENT_SEC,
    redirect_uri = REDIRECT_URI,
    scope = SCOPE
  )
  auth_url = sp_oauth.get_authorize_url()
  print(auth_url)
  return redirect(auth_url)

@app.route("/callback")
def callback():
  sp_oauth = spotipy.oauth2.SpotifyOAuth(
    client_id = CLIENT_ID,
    client_secret = CLIENT_SEC,
    redirect_uri = REDIRECT_URI,
    scope = SCOPE
  )
  session.clear()
  code = request.args.get('code')
  token_info = sp_oauth.get_access_token(code)
  session["token_info"] = token_info
  return redirect("/")

def get_token(session):
  token_valid = False
  token_info = session.get("token_info", {})

  # Checking if the session already has a token stored
  if not (session.get('token_info', False)):
      token_valid = False
      return token_info, token_valid

  # Checking if token has expired
  now = int(time.time())
  is_token_expired = session.get('token_info').get('expires_at') - now < 60

  # Refreshing token if it has expired
  if (is_token_expired):
      # Don't reuse a SpotifyOAuth object because they store token info and you could leak user tokens if you reuse a SpotifyOAuth object
      sp_oauth = spotipy.oauth2.SpotifyOAuth(
        client_id = CLIENT_ID,
        client_secret = CLIENT_SEC,
        redirect_uri = REDIRECT_URI,
        scope = SCOPE
      )
      token_info = sp_oauth.refresh_access_token(session.get('token_info').get('refresh_token'))

  token_valid = True
  return token_info, token_valid
  
if __name__ == "__main__":
  app.run(host='0.0.0.0')