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

DB_PATH = Path(__file__).parent / "gimbo.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create tables if they don't exist yet. Safe to call every startup."""
    conn = get_connection()
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Games (backs the AddEntryModal -> entry_created signal)
# ---------------------------------------------------------------------------

def create_game(entry: dict) -> int:
    """
    entry is the dict emitted by AddEntryModal.entry_created:
    {title, platform, description, image_path}. The `cover_path` column name
    in the games table stays as-is (it's just the DB's internal naming);
    this function is what maps AddEntryModal's `image_path` key onto it.
    """
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO games (title, platform, cover_path, description) VALUES (?, ?, ?, ?)",
        (
            entry["title"],
            entry.get("platform"),
            entry.get("image_path"),   # <-- changed from entry.get("cover_path")
            entry.get("description"),
        ),
    )
    conn.commit()
    game_id = cur.lastrowid
    conn.close()
    return game_id


def get_all_games() -> list[sqlite3.Row]:
    """Used lazily by the journal list page when it's shown."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM games ORDER BY created_at DESC").fetchall()
    conn.close()
    return rows


def get_game(game_id: int) -> sqlite3.Row | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    conn.close()
    return row


def delete_game(game_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM games WHERE id = ?", (game_id,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Sessions (backs session_saved signal)
# ---------------------------------------------------------------------------

def create_session(session: dict) -> int:
    """
    session is the dict emitted by WritingPage.session_saved:
    {game_id, text, playtime_minutes, screenshot_path}.
    game_id is already inside the dict, so it doesn't need to be passed separately.
    """
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO sessions (game_id, duration_minutes, notes, screenshot_path) VALUES (?, ?, ?, ?)",
        (
            session.get("game_id"),
            session.get("playtime_minutes"),
            session.get("text"),
            session.get("screenshot_path"),
        ),
    )
    conn.commit()
    session_id = cur.lastrowid
    conn.close()
    return session_id


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
    entry uses the same shape as create_game: {title, platform, description, image_path}.
    Updates the existing row in place rather than inserting a new one.
    """
    conn = get_connection()
    conn.execute(
        "UPDATE games SET title = ?, platform = ?, cover_path = ?, description = ? WHERE id = ?",
        (
            entry.get("title"),
            entry.get("platform"),
            entry.get("image_path"),
            entry.get("description"),
            game_id,
        ),
    )
    conn.commit()
    conn.close()


def get_highlight_entries() -> list[sqlite3.Row]:
    """
    Games that have at least one review, joined with:
      - their most recent review (rating, body)
      - aggregated session stats (total playtime, session count)
    Used by HighlightWindow.
    """
    conn = get_connection()
    query = """
        SELECT
            g.id            AS id,
            g.title         AS title,
            g.cover_path    AS cover_path,
            g.platform      AS platform,
            r.rating        AS rating,
            r.body          AS body,
            r.created_at    AS review_created_at,
            COALESCE(s.total_minutes, 0)  AS total_minutes,
            COALESCE(s.session_count, 0)  AS session_count
        FROM games g
        JOIN reviews r ON r.id = (
            SELECT id FROM reviews
            WHERE game_id = g.id
            ORDER BY created_at DESC
            LIMIT 1
        )
        LEFT JOIN (
            SELECT game_id,
                   SUM(duration_minutes) AS total_minutes,
                   COUNT(*) AS session_count
            FROM sessions
            GROUP BY game_id
        ) s ON s.game_id = g.id
        ORDER BY r.created_at DESC
    """
    rows = conn.execute(query).fetchall()
    conn.close()
    return rows


def get_all_screenshots(game_id: int | None = None) -> list[sqlite3.Row]:
    """
    Every session screenshot across the whole library, newest first.
    Pass game_id to restrict to one game (used by the filter modal).
    Joins in the game title in case you want it later (e.g. tooltip/caption).
    """
    conn = get_connection()
    base_query = """
        SELECT
            s.id              AS session_id,
            s.game_id         AS game_id,
            s.screenshot_path AS screenshot_path,
            s.created_at      AS created_at,
            g.title           AS title
        FROM sessions s
        JOIN games g ON g.id = s.game_id
        WHERE s.screenshot_path IS NOT NULL AND s.screenshot_path != ''
    """
    if game_id is not None:
        rows = conn.execute(
            base_query + " AND s.game_id = ? ORDER BY s.created_at DESC",
            (game_id,),
        ).fetchall()
    else:
        rows = conn.execute(base_query + " ORDER BY s.created_at DESC").fetchall()
    conn.close()
    return rows