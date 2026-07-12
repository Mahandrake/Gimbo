"""
db.py - single place that owns the SQLite connection for Gimbo.

Usage:
    from db import init_db, create_game, get_all_games, ...

    # once, at app startup (e.g. top of main.py, before the window is shown)
    init_db()

Design notes:
- One short-lived connection per call (sqlite3 handles this fine at Gimbo's scale).
  If you notice performance issues later with many rapid calls, we can switch to
  a persistent connection held on a QObject - not needed yet.
- row_factory = sqlite3.Row means results behave like dicts: row["title"], row["id"], etc.
- Foreign keys are ON, so deleting a game cascades to its sessions/reviews.
"""

import sqlite3
from pathlib import Path
import os
import sys
from pathlib import Path

from config.settings import BASE_DIR  # already frozen-aware, see settings.py


def _get_user_data_dir() -> Path:
    """Where gimbo.db should actually live once the app is packaged.
    Falls back to the project folder when running from source, so
    behavior for you during development doesn't change at all."""
    if not getattr(sys, "frozen", False):
        return Path(__file__).parent

    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:  # Linux and other POSIX
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    data_dir = base / "Gimbo"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def get_rawg_cache_dir() -> Path:
    """Local disk cache for downloaded RAWG cover art, so a game already in
    the library never re-downloads its cover on a later launch."""
    cache_dir = _get_user_data_dir() / "rawg_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir

DB_PATH = _get_user_data_dir() / "gimbo.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_games_columns(conn: sqlite3.Connection) -> None:
    existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(games)").fetchall()}
    if "is_archived" not in existing_cols:
        conn.execute("ALTER TABLE games ADD COLUMN is_archived INTEGER NOT NULL DEFAULT 0")
    if "is_tracked" not in existing_cols:
        conn.execute("ALTER TABLE games ADD COLUMN is_tracked INTEGER NOT NULL DEFAULT 0")

    # RAWG integration columns (v1.0.4) - cached metadata from the RAWG API,
    # written once when a game is created/edited via AddEntryModal so the
    # Journal detail panel never has to re-fetch anything to display it.
    rawg_columns = {
        "rawg_id": "INTEGER",
        "rawg_rating": "REAL",
        "rawg_metacritic": "INTEGER",
        "rawg_playtime": "INTEGER",
        "rawg_released": "TEXT",
        "rawg_genres": "TEXT",
    }
    for col, col_type in rawg_columns.items():
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE games ADD COLUMN {col} {col_type}")

    conn.commit()


def init_db() -> None:
    """Create tables if they don't exist yet. Safe to call every startup."""
    conn = get_connection()
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    _ensure_games_columns(conn)
    conn.close()


# ---------------------------------------------------------------------------
# Games (backs the AddEntryModal -> entry_created signal)
# ---------------------------------------------------------------------------

def create_game(entry: dict) -> int:
    """
    entry is the dict emitted by AddEntryModal.entry_created:
    {title, platform, description, image_path, rawg_id, rawg_rating,
    rawg_metacritic, rawg_playtime, rawg_released, rawg_genres}.
    The rawg_* keys are optional/None when the game wasn't linked to RAWG.
    """
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO games
           (title, platform, cover_path, description,
            rawg_id, rawg_rating, rawg_metacritic, rawg_playtime, rawg_released, rawg_genres)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            entry["title"],
            entry.get("platform"),
            entry.get("image_path"),
            entry.get("description"),
            entry.get("rawg_id"),
            entry.get("rawg_rating"),
            entry.get("rawg_metacritic"),
            entry.get("rawg_playtime"),
            entry.get("rawg_released"),
            entry.get("rawg_genres"),
        ),
    )
    conn.commit()
    game_id = cur.lastrowid
    conn.close()
    return game_id


def get_all_games() -> list[sqlite3.Row]:
    """All games regardless of archive status. Used by Index, Photo Book
    (filter modal), and anywhere else that should NOT be affected by
    archiving a game out of the Journal."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM games ORDER BY created_at DESC").fetchall()
    conn.close()
    return rows


def get_journal_games() -> list[sqlite3.Row]:
    """Games shown on the Journal page - excludes archived games. Kept
    separate from get_all_games() so Index, Photo Book, and Highlights
    are unaffected by archiving."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM games WHERE is_archived = 0 ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return rows


def get_archived_games() -> list[sqlite3.Row]:
    """Used by the Archive List modal."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM games WHERE is_archived = 1 ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return rows


def get_game(game_id: int) -> sqlite3.Row | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    conn.close()
    return row


def delete_game(game_id: int) -> None:
    """Permanent delete - cascades to sessions, session_screenshots, and
    reviews via the ON DELETE CASCADE foreign keys in schema.sql. Used both
    for the original Journal 'Delete' action and for the Archive List's
    'Delete Permanently' action."""
    conn = get_connection()
    conn.execute("DELETE FROM games WHERE id = ?", (game_id,))
    conn.commit()
    conn.close()


def archive_game(game_id: int) -> None:
    """Moves a game to the archive. Nothing is deleted - sessions, reviews,
    and screenshots are untouched; the game simply stops appearing in
    get_journal_games()."""
    conn = get_connection()
    conn.execute("UPDATE games SET is_archived = 1 WHERE id = ?", (game_id,))
    conn.commit()
    conn.close()


def restore_game(game_id: int) -> None:
    """Moves a game back out of the archive and into the Journal."""
    conn = get_connection()
    conn.execute("UPDATE games SET is_archived = 0 WHERE id = ?", (game_id,))
    conn.commit()
    conn.close()


def set_game_tracked(game_id: int, tracked: bool) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE games SET is_tracked = ? WHERE id = ?",
        (1 if tracked else 0, game_id),
    )
    conn.commit()
    conn.close()


def get_tracked_count() -> int:
    """Archived games are excluded from the count, so archiving a tracked
    game frees up a tracking slot without requiring the user to untrack
    it first."""
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) AS count FROM games WHERE is_tracked = 1 AND is_archived = 0"
    ).fetchone()
    conn.close()
    return row["count"] if row else 0


def game_has_review(game_id: int) -> bool:
    """Used by JournalWindow to decide whether the Archive button should be
    shown - a game counts as 'finished' if it has a review row, matching
    the is_finished-via-review pattern used elsewhere."""
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM reviews WHERE game_id = ? LIMIT 1", (game_id,)
    ).fetchone()
    conn.close()
    return row is not None


# ---------------------------------------------------------------------------
# Sessions (backs session_saved signal)
# ---------------------------------------------------------------------------

def create_session(session: dict) -> int:
    """
    session is the dict emitted by WritingPage.session_saved:
    {game_id, text, playtime_minutes, screenshot_paths}.
    screenshot_paths is a list now (unlimited) - one row per path goes
    into session_screenshots instead of a single column on sessions.
    """
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO sessions (game_id, duration_minutes, notes) VALUES (?, ?, ?)",
        (
            session.get("game_id"),
            session.get("playtime_minutes"),
            session.get("text"),
        ),
    )
    session_id = cur.lastrowid

    for path in session.get("screenshot_paths") or []:
        if path:
            conn.execute(
                "INSERT INTO session_screenshots (session_id, screenshot_path) VALUES (?, ?)",
                (session_id, path),
            )

    conn.commit()
    conn.close()
    return session_id


def get_screenshots_for_session(session_id: int) -> list[sqlite3.Row]:
    """Used by DiaryWindow to render every screenshot for a session card."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM session_screenshots WHERE session_id = ? ORDER BY created_at ASC",
        (session_id,),
    ).fetchall()
    conn.close()
    return rows


def get_sessions_for_game(game_id: int) -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM sessions WHERE game_id = ? ORDER BY created_at DESC", (game_id,)
    ).fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Reviews (backs review_saved signal)
# ---------------------------------------------------------------------------

def create_review(game_id: int, review: dict) -> int:
    """review expected keys: rating, body."""
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO reviews (game_id, rating, body) VALUES (?, ?, ?)",
        (game_id, review.get("rating"), review.get("body")),
    )
    conn.commit()
    review_id = cur.lastrowid
    conn.close()
    return review_id


def get_reviews_for_game(game_id: int) -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM reviews WHERE game_id = ? ORDER BY created_at DESC", (game_id,)
    ).fetchall()
    conn.close()
    return rows


def update_game(game_id: int, entry: dict) -> None:
    """
    Same shape as create_game. Doesn't touch is_archived/is_tracked, so
    editing a game never disturbs its archive/track state. rawg_* fields
    ARE overwritten here - AddEntryModal is responsible for carrying
    forward the existing linkage when the user doesn't re-pick from RAWG,
    so this stays a plain "write what you were given" function.
    """
    conn = get_connection()
    conn.execute(
        """UPDATE games
           SET title = ?, platform = ?, cover_path = ?, description = ?,
               rawg_id = ?, rawg_rating = ?, rawg_metacritic = ?,
               rawg_playtime = ?, rawg_released = ?, rawg_genres = ?
           WHERE id = ?""",
        (
            entry.get("title"),
            entry.get("platform"),
            entry.get("image_path"),
            entry.get("description"),
            entry.get("rawg_id"),
            entry.get("rawg_rating"),
            entry.get("rawg_metacritic"),
            entry.get("rawg_playtime"),
            entry.get("rawg_released"),
            entry.get("rawg_genres"),
            game_id,
        ),
    )
    conn.commit()
    conn.close()


def get_highlight_entries() -> list[sqlite3.Row]:
    conn = get_connection()
    query = """
            SELECT g.id                         AS id,
                   g.title                      AS title,
                   g.cover_path                 AS cover_path,
                   g.platform                   AS platform,
                   r.id                         AS review_id,
                   r.rating                     AS rating,
                   r.body                       AS body,
                   r.created_at                 AS review_created_at,
                   COALESCE(s.total_minutes, 0) AS total_minutes,
                   COALESCE(s.session_count, 0) AS session_count
            FROM games g
                     JOIN reviews r ON r.id = (SELECT id
                                               FROM reviews
                                               WHERE game_id = g.id
                                               ORDER BY created_at DESC
                LIMIT 1
                )
                LEFT JOIN (
            SELECT game_id, SUM (duration_minutes) AS total_minutes, COUNT (*) AS session_count
            FROM sessions
            GROUP BY game_id
                ) s
            ON s.game_id = g.id
            ORDER BY r.created_at DESC \
            """
    rows = conn.execute(query).fetchall()
    conn.close()
    return rows


def get_all_screenshots(game_id: int | None = None) -> list[sqlite3.Row]:
    """
    Every session screenshot across the whole library, newest first.
    Pass game_id to restrict to one game (used by the filter modal).
    """
    conn = get_connection()
    base_query = """
                 SELECT ss.id              AS screenshot_id,
                        ss.session_id      AS session_id,
                        ss.screenshot_path AS screenshot_path,
                        ss.created_at      AS created_at,
                        s.game_id          AS game_id,
                        g.title            AS title
                 FROM session_screenshots ss
                          JOIN sessions s ON s.id = ss.session_id
                          JOIN games g ON g.id = s.game_id \
                 """
    if game_id is not None:
        rows = conn.execute(
            base_query + " WHERE s.game_id = ? ORDER BY ss.created_at DESC",
            (game_id,),
        ).fetchall()
    else:
        rows = conn.execute(base_query + " ORDER BY ss.created_at DESC").fetchall()
    conn.close()
    return rows


def update_session(session_id: int, session: dict) -> None:
    """session keys: text, playtime_minutes. Screenshots aren't touched here -
    removing a screenshot from a session is handled separately via
    delete_screenshot, from the Photo Book."""
    conn = get_connection()
    conn.execute(
        "UPDATE sessions SET duration_minutes = ?, notes = ? WHERE id = ?",
        (session.get("playtime_minutes"), session.get("text"), session_id),
    )
    conn.commit()
    conn.close()


def delete_session(session_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


def update_review(review_id: int, review: dict) -> None:
    """review keys: rating, body."""
    conn = get_connection()
    conn.execute(
        "UPDATE reviews SET rating = ?, body = ? WHERE id = ?",
        (review.get("rating"), review.get("body"), review_id),
    )
    conn.commit()
    conn.close()


def delete_review(review_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
    conn.commit()
    conn.close()


def delete_screenshot(screenshot_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM session_screenshots WHERE id = ?", (screenshot_id,))
    conn.commit()
    conn.close()


def add_screenshot_to_session(session_id: int, path: str) -> int:
    """Adds one screenshot to an existing session - used when editing a
    session in DiaryWindow to add more screenshots after the fact."""
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO session_screenshots (session_id, screenshot_path) VALUES (?, ?)",
        (session_id, path),
    )
    conn.commit()
    screenshot_id = cur.lastrowid
    conn.close()
    return screenshot_id