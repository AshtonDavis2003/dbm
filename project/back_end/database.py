from __future__ import annotations
import sqlite3
from pathlib import Path

# ── connection wrapper ────────────────────────────────────────────────────────────────────────────
class Database:
    def __init__(self, db_path: str | Path = "roommate.db") -> None:
        self.db_path = Path(db_path)
        self.conn: sqlite3.Connection | None = None
        self._cur: sqlite3.Cursor | None = None

    # ── open / close ────────────────────────────────────────────────────────────────────────────
    def connect(self) -> None:
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row

    def disconnect(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None
            self._cur = None

    # ── SQL helpers ────────────────────────────────────────────────────────────────────────────
    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        if self.conn is None:
            raise RuntimeError("connect() first")
        cur = self.conn.cursor()
        cur.execute(sql, params)
        self.conn.commit()
        self._cur = cur
        return cur

    def fetchone(self):
        return self._cur.fetchone() if self._cur else None

    def fetchall(self):
        return self._cur.fetchall() if self._cur else []

    # ── schema ────────────────────────────────────────────────────────────────────────────
    def init_database(self) -> None:
        self.connect()
        self.conn.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS Student (
                StudentId  INTEGER PRIMARY KEY,
                Name       TEXT UNIQUE,
                WantsAC    INTEGER,
                WantsDining INTEGER,
                WantsKitchen INTEGER,
                WantsPrivateBathroom INTEGER
            );
            CREATE TABLE IF NOT EXISTS Building (
                BuildingId INTEGER PRIMARY KEY,
                Name       TEXT
            );
            CREATE TABLE IF NOT EXISTS Room (
                BuildingId       INTEGER,
                RoomNumber       INTEGER,
                HasKitchen       INTEGER,
                PrivateBathrooms INTEGER,
                PRIMARY KEY (BuildingId, RoomNumber)
            );
            CREATE TABLE IF NOT EXISTS Assignment (
                StudentId  INTEGER PRIMARY KEY,
                BuildingId INTEGER,
                RoomNumber INTEGER
            );
            """
        )
        self.conn.commit()

    # ── demo data ────────────────────────────────────────────────────────────────────────────
    def seed_data(self) -> None:
        self.execute("SELECT COUNT(*) FROM Room")
        if self.fetchone()[0]:
            return

        self.execute(
            """
            INSERT OR IGNORE INTO Building (BuildingId, Name) VALUES
                (1,'Maples West'),
                (2,'Maples South'),
                (3,'Maples East')
            """
        )

        rooms = [
            (1, 101, 0, 0), (1, 102, 1, 0), (1, 103, 1, 1),
            (2, 201, 0, 0), (2, 202, 0, 1), (2, 203, 1, 1),
            (3, 301, 0, 0), (3, 302, 1, 0), (3, 303, 1, 1),
        ]
        students = [
            (1, "Alice",   1, 0, 0, 0),
            (2, "Bob",     1, 1, 0, 0),
            (3, "Charlie", 1, 1, 1, 0),
            (4, "Dana",    1, 1, 1, 1),
        ]

        self.conn.executemany(
            "INSERT INTO Room (BuildingId, RoomNumber, HasKitchen, PrivateBathrooms) VALUES (?,?,?,?)",
            rooms,
        )
        self.conn.executemany(
            "INSERT INTO Student (StudentId, Name, WantsAC, WantsDining, WantsKitchen, WantsPrivateBathroom) VALUES (?,?,?,?,?,?)",
            students,
        )
        self.conn.commit()
#────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────