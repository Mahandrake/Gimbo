"""
services/rawg_client.py - thin async wrapper around the RAWG Video Games
Database API (https://rawg.io/apidocs). Used ONLY by AddEntryModal on the
Journal page for title autocomplete + metadata lookup. No other page
should import this.

Design notes:
- Uses QNetworkAccessManager (not `requests`) so calls never block the Qt
  event loop - no worker threads needed, replies arrive as signals, same
  spirit as this codebase's existing signal-driven decoupling.
- In-memory caches (search-by-query, details-by-id) avoid re-hitting the
  API while a user is typing or re-opening the edit modal in one session.
- Once a game is saved, its RAWG fields live on the `games` row and its
  cover is cached to disk (see db.get_rawg_cache_dir) - a saved game never
  re-fetches anything on later launches.
"""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QUrl, QUrlQuery
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from config.settings import RAWG_API_KEY, RAWG_BASE_URL
from db import get_rawg_cache_dir


class RawgClient(QObject):
    """One instance is owned by AddEntryModal."""

    suggestions_ready = Signal(list)   # list[dict]: id, name, released, background_image
    details_ready = Signal(dict)       # full game details dict, see _on_details_finished
    cover_ready = Signal(str, str)     # (image_url, local_path)
    error = Signal(str)

    SEARCH_PAGE_SIZE = 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = QNetworkAccessManager(self)
        self._search_cache: dict[str, list[dict]] = {}
        self._details_cache: dict[int, dict] = {}
        self._active_search_reply: QNetworkReply | None = None

    # ------------------------------------------------------------------
    # Search / autocomplete
    # ------------------------------------------------------------------

    def search_games(self, query: str) -> None:
        query = query.strip()
        if not query or not RAWG_API_KEY:
            self.suggestions_ready.emit([])
            return

        cached = self._search_cache.get(query.lower())
        if cached is not None:
            self.suggestions_ready.emit(cached)
            return

        # Cancel any in-flight search so a stale reply can't clobber newer
        # results once the user has kept typing.
        if self._active_search_reply is not None:
            self._active_search_reply.abort()
            self._active_search_reply = None

        url = QUrl(f"{RAWG_BASE_URL}/games")
        q = QUrlQuery()
        q.addQueryItem("key", RAWG_API_KEY)
        q.addQueryItem("search", query)
        q.addQueryItem("page_size", str(self.SEARCH_PAGE_SIZE))
        url.setQuery(q)

        reply = self._manager.get(QNetworkRequest(url))
        self._active_search_reply = reply
        reply.finished.connect(lambda: self._on_search_finished(reply, query))

    def _on_search_finished(self, reply: QNetworkReply, query: str) -> None:
        if reply is self._active_search_reply:
            self._active_search_reply = None

        if reply.error() != QNetworkReply.NoError:
            reply.deleteLater()
            if reply.error() != QNetworkReply.OperationCanceledError:
                self.error.emit(f"RAWG search failed: {reply.errorString()}")
            return

        try:
            data = json.loads(bytes(reply.readAll()).decode("utf-8"))
        except Exception as exc:
            reply.deleteLater()
            self.error.emit(f"RAWG search returned bad data: {exc}")
            return
        reply.deleteLater()

        results = [
            {
                "id": item.get("id"),
                "name": item.get("name", ""),
                "released": item.get("released"),
                "background_image": item.get("background_image"),
            }
            for item in data.get("results", [])
        ]
        self._search_cache[query.lower()] = results
        self.suggestions_ready.emit(results)

    # ------------------------------------------------------------------
    # Game details
    # ------------------------------------------------------------------

    def get_game_details(self, rawg_id: int) -> None:
        cached = self._details_cache.get(rawg_id)
        if cached is not None:
            self.details_ready.emit(cached)
            return

        if not RAWG_API_KEY:
            self.error.emit("No RAWG API key configured.")
            return

        url = QUrl(f"{RAWG_BASE_URL}/games/{rawg_id}")
        q = QUrlQuery()
        q.addQueryItem("key", RAWG_API_KEY)
        url.setQuery(q)

        reply = self._manager.get(QNetworkRequest(url))
        reply.finished.connect(lambda: self._on_details_finished(reply, rawg_id))

    def _on_details_finished(self, reply: QNetworkReply, rawg_id: int) -> None:
        if reply.error() != QNetworkReply.NoError:
            reply.deleteLater()
            self.error.emit(f"RAWG details fetch failed: {reply.errorString()}")
            return

        try:
            data = json.loads(bytes(reply.readAll()).decode("utf-8"))
        except Exception as exc:
            reply.deleteLater()
            self.error.emit(f"RAWG details returned bad data: {exc}")
            return
        reply.deleteLater()

        genres = ", ".join(g.get("name", "") for g in (data.get("genres") or []))

        details = {
            "rawg_id": data.get("id"),
            "name": data.get("name", ""),
            "background_image": data.get("background_image"),
            "rating": data.get("rating"),           # 0-5 RAWG community score
            "metacritic": data.get("metacritic"),   # 0-100 or None
            "playtime": data.get("playtime"),       # avg hours-to-beat estimate
            "released": data.get("released"),       # "YYYY-MM-DD" or None
            "description": data.get("description_raw", "") or "",
            "genres": genres,
        }
        self._details_cache[rawg_id] = details
        self.details_ready.emit(details)

    # ------------------------------------------------------------------
    # Cover image download + on-disk cache
    # ------------------------------------------------------------------

    def fetch_cover(self, rawg_id: int, image_url: str | None) -> None:
        if not image_url:
            return

        local_path = get_rawg_cache_dir() / f"{rawg_id}.jpg"
        if local_path.exists():
            self.cover_ready.emit(image_url, str(local_path))
            return

        reply = self._manager.get(QNetworkRequest(QUrl(image_url)))
        reply.finished.connect(lambda: self._on_cover_finished(reply, image_url, local_path))

    def _on_cover_finished(self, reply: QNetworkReply, image_url: str, local_path: Path) -> None:
        if reply.error() != QNetworkReply.NoError:
            reply.deleteLater()
            self.error.emit(f"Cover download failed: {reply.errorString()}")
            return

        data = bytes(reply.readAll())
        reply.deleteLater()
        try:
            local_path.write_bytes(data)
        except OSError as exc:
            self.error.emit(f"Could not cache cover image: {exc}")
            return

        self.cover_ready.emit(image_url, str(local_path))