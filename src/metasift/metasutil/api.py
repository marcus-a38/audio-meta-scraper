from __future__ import annotations

from argparse import ArgumentTypeError
from contextlib import closing
from itertools import chain
from os import getcwd
from pathlib import Path
from sqlite3 import Connection, DatabaseError
from typing import Union

from . import log
from .utils import MetaParams, sift, sift_sys, analyze

DEFAULT_SEARCH_PATH = Path(".")
DEFAULT_DATABASE_PATH = DEFAULT_SEARCH_PATH / 'data' / 'metasift.db'

CREATE_TABLE = """CREATE TABLE IF NOT EXISTS file (
                    path varchar(255) PRIMARY KEY, 
                    format varchar(5),
                    title varchar(255), 
                    artist varchar(255), 
                    album varchar(255), 
                    genre varchar(255), 
                    date datetime,
                    duration time,
                    comment varchar(255)
                )
            """

VALID_SQLITE_EXTS = [
    ".db",
    ".sdb",
    ".s3db",
    ".db3" ".sqlite",
    ".sqlite3",
    ".database",
]


class MetaSiftDB(Connection):
    """Encapsulates sqlite3.Connection class with minor additions."""

    def __init__(self, db: Path):
        self.path = db
        self.acquire_backup()

    def acquire_backup(self):
        """Establishes backup DB and acquires a connection to it."""

        # Make sure the `metasift_backup` directory exists
        parent = self.path.parent
        backup_dir = parent / "metasift_backup"
        backup_dir.mkdir(exist_ok=True)

        # Make sure the backup file exists
        self.backup_db_path = backup_dir / "metasift.backup"
        self.backup_db_path.touch()

        self.backup_db = Connection(self.backup_db_path)

    def acquire_self(self):
        """Instantiate the superclass (sqlite3.Connection), recover on error."""

        # Instantiate sqlite3.Connection at self.path
        super().__init__(self.path)

        with closing(self.cursor()) as cursor:

            # Check database integrity
            try:
                cursor.execute("PRAGMA integrity_check")

            # Integrity check failed, attempt recovery
            except DatabaseError as err:
                log.write_log(
                    log.WARNING,
                    "DB integrity check failed! Recovering... More details:",
                )
                log.write_log(log.DEBUG, err)
                self.recover()

            # Create file table if it doesn't already exist
            cursor.execute(CREATE_TABLE)

        # Acquire backup file for DB
        self.acquire_backup()

    def empty_table(self):
        with closing(self.cursor()) as cursor:
            cursor.execute("DELETE FROM file")

    def dump_contents(self):
        """Backup the DB (dump contents) ."""

        # Make sure we commit changes to DB before backing up
        self.commit()

        # Dump and close everything up
        with self.backup_db:
            self.backup(self.backup_db)
        self.backup_db.close()
        self.close()

    def pull_backup(self):
        """Pull the contents of the backup DB into the main DB."""

        with self:
            self.backup_db.backup(self)
        self.backup_db.close()

    def recover(self):
        """Delete and recreate the database using backup DB"""

        self.close()

        # Delete the database entirely and recreate it at same path
        self.path.unlink()
        self.path.touch()

        # Attempt to reacquire connection and pull backup data
        self.acquire_self()
        self.pull_backup()

        # We need to consider a potential circular issue here, say
        # the database failed to open properly and we recover, but
        # it continues to fail upon recovery. We will infinitely be
        # attempting to acquire a new connection and recovering.

        # This scenario is unlikely to happen, but is still evidently
        # a potential issue. Address later.

    def insert(self, metadata: list[MetaParams]) -> None:
        """Bulk inserts a list of audio file metadata tuples."""

        log.write_log(log.INFO, "Inserting data...")

        with closing(self.cursor()) as cursor:

            cursor.executemany(
                """INSERT INTO file (
                        path, 
                        format,
                        title, 
                        artist, 
                        album,
                        genre, 
                        date,
                        duration,
                        comment
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO NOTHING;
                """,
                metadata,
            )
        log.write_log(log.INFO, "Data successfully inserted.")
        # Consider adding error handling for safety ...


def validate_path_or_paths(path_or_paths: Union[list[Path], Path]) -> None:
    """Ensures that the provided search path(s) exist before proceeding.
    
    Returns nothing, but raises ArgumentTypeError if the path is invalid.
    """

    for path in path_or_paths:
        if not path.exists() or path.is_file():
            raise ArgumentTypeError("'%s' is not a valid path." % path)


def validate_db_path(path: Path) -> Path:
    """Ensures that the provided db path has the correct file extension.

    If the path is a non-existent db file, attempt to create the
    parent directory(ies) and place a new db file in the lowest-level
    directory. Ditto for paths that are already-existing directories.
    """

    if path.is_file():  # Exists and is a file

        if path.suffix not in VALID_SQLITE_EXTS:
            raise ArgumentTypeError(
                "'%s' is not a valid sqlite '.db' file." % str(path)
            )
        db = path

    else:

        # Check if it's a DB file that doesn't exist
        if path.suffix in VALID_SQLITE_EXTS:

            try:
                path.parent.mkdir(parents=True, exist_ok=True)
            except:
                raise ArgumentTypeError(
                    "'%s' is not a valid path." % str(path)
                )
            db = path

        # Must be a directory, place new DB file in it
        else:
            db = path / "metasift.db"

    db.touch()
    return db


def handle_main(args: Namespace) -> None:
    """Handles arguments passed through the commandline."""

    # Validate paths for log, db, and search before proceeding
    validate_path_or_paths(args.path)
    db_path = validate_db_path(args.db)
    path_to_log = db_path.parent / "metas.log"
    path_to_log.touch()

    log.logger_setup(path_to_log, silent=args.silent)

    # Acquire database connection
    conn = MetaSiftDB(db_path)
    conn.acquire_self()

    # Empty out the DB table if overwrite is enabled
    if args.overwrite:
        conn.empty_table()

    # System search using sift_sys()
    if args.everything:
        results = analyze(path_to_log, sift_sys(), silent=args.silent)

    # Recursive or nonrecursive search using sift()
    else:
        sift_list = [
            sift(path, recursive=args.recursive) for path in args.path
        ]
        sifted = chain.from_iterable(sift_list)
        results = analyze(path_to_log, sifted, silent=args.silent)

    # Insert the results and dump the main DB contents into backup
    if results:
        conn.insert(results)
        conn.dump_contents()
    else:
        log.write_log(log.WARNING, "MetaSift did not find any results.")