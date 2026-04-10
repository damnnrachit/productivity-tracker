from __future__ import annotations

import os

import requests
from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required

spotify_bp = Blueprint("spotify", __name__)


def get_spotify_headers() -> dict[str, str] | None:
    token = os.environ.get("SPOTIFY_ACCESS_TOKEN", "").strip()
    if not token:
        return None
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def fetch_current_track() -> dict[str, str] | None:
    headers = get_spotify_headers()
    if headers is None:
        return None

    response = requests.get(
        "https://api.spotify.com/v1/me/player/currently-playing",
        headers=headers,
        timeout=10,
    )
    if response.status_code in {204, 202}:
        return {"name": "No active track", "artist": "-", "album": "-"}
    if response.status_code >= 400:
        return {"name": "Unable to fetch track", "artist": "Spotify API error", "album": "-"}

    payload = response.json()
    item = payload.get("item") or {}
    artists = item.get("artists") or []
    return {
        "name": item.get("name", "Unknown"),
        "artist": ", ".join(a.get("name", "") for a in artists if a.get("name")) or "Unknown",
        "album": (item.get("album") or {}).get("name", "Unknown"),
    }


def control_playback(action: str) -> bool:
    headers = get_spotify_headers()
    if headers is None:
        return False

    endpoint = "play" if action == "play" else "pause"
    device_id = os.environ.get("SPOTIFY_DEVICE_ID", "").strip()
    url = f"https://api.spotify.com/v1/me/player/{endpoint}"
    if device_id:
        url = f"{url}?device_id={device_id}"

    response = requests.put(url, headers=headers, timeout=10)
    return response.status_code in {200, 202, 204}


@spotify_bp.get("/spotify")
@login_required
def spotify_page():
    has_token = get_spotify_headers() is not None
    track = fetch_current_track() if has_token else None
    return render_template("spotify.html", has_token=has_token, track=track)


@spotify_bp.post("/spotify/play")
@login_required
def spotify_play():
    if not control_playback("play"):
        flash("Could not play track. Check Spotify token/device.", "info")
    else:
        flash("Playback started.", "success")
    return redirect(url_for("spotify.spotify_page"))


@spotify_bp.post("/spotify/pause")
@login_required
def spotify_pause():
    if not control_playback("pause"):
        flash("Could not pause track. Check Spotify token/device.", "info")
    else:
        flash("Playback paused.", "success")
    return redirect(url_for("spotify.spotify_page"))
