from __future__ import annotations

import concurrent.futures as cfutures
import platform

from enum import Enum
from itertools import chain
from pathlib import Path
from multiprocessing import Lock, Manager, Process
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from typing import Iterator, NamedTuple, Union

from . import log


class FileType(Enum):
    """Basic enumerator for FLAC/MPEG-4 files."""

    MPEG4 = 0
    FLAC = 1


class MetaParams(NamedTuple):
    """Encapsulates metadata results from an analyzed audio file."""

    path: str
    fformat: str
    title: str
    artist: str
    album: str
    genre: str
    date: str
    duration: str
    comment: str


class SiftResult(NamedTuple):
    """Encapsulates audio file results from sift routine."""

    path: Path
    ftype: FileType


VALID_FILE_EXTS = {
    ".flac": FileType.FLAC,
    ".mp4": FileType.MPEG4,
    ".m4a": FileType.MPEG4,
}

# Prevents logger race conditions 
lock = Lock()


def analyze_file(file: SiftResult, log_queue: Queue) -> Union[MetaParams, None]:
    """Pulls and returns metadata from an audio file."""

    def reformat_seconds(time: float) -> str:
        """Returns reformatted seconds (float) as HH:MM:SS (str)."""

        minutes, seconds = divmod(time, 60)
        hours, minutes = divmod(minutes, 60)

        return "%d:%02d:%02d" % (hours, minutes, seconds)

    with lock:

        # Create a unique logger for the current process, submit msgs to queue
        log.configure_logger(log_queue)
        log.write_log(log.INFO, f"Processing {file.path}...")

        def instantiate_file(is_flac: bool):
            return FLAC(str(file.path)) if is_flac else MP4(str(file.path))

        # Metadata codes (tags) for FLAC and MPEG-4 differ.
        # Learn more @ https://mutagen.readthedocs.io/en/latest/api/
        if file.ftype == FileType.FLAC:
            tags = {
                "t": "title",
                "a": "artist",
                "s": "album",
                "g": "genre",
                "d": "date",
                "c": "comment",
            }
        else:
            tags = {
                "t": "\xa9nam",
                "a": "\xa9ART",
                "s": "\xa9alb",
                "g": "\xa9gen",
                "d": "\xa9day",
                "c": "\xa9cmt",
            }

        # Attempt to open the file and instantiate a FLAC or MP4 object
        try:
            file_obj = instantiate_file(file.ftype)

        # Issue opening or instantiating with provided file
        except Exception as err:
            log.write_log(log.WARNING, f"Could not open {file.path}.")
            log.write_log(log.DEBUG, err)
            return None
        
        # Attempt to pull metadata from file
        try:
            data = MetaParams(
                path=str(file.path),
                fformat=file.path.suffix.lstrip("."),
                title=file_obj.get(tags.get("t"), ["NULL"])[0],
                artist=file_obj.get(tags.get("a"), ["NULL"])[0],
                album=file_obj.get(tags.get("s"), ["NULL"])[0],
                genre=file_obj.get(tags.get("g"), ["NULL"])[0],
                date=file_obj.get(tags.get("d"), ["NULL"])[0],
                duration=reformat_seconds(file_obj.info.length),
                comment=file_obj.get(tags.get("c"), ["NULL"])[0],
            )

        # Issue reading metadata
        except Exception as err:
            log.write_log(log.WARNING, f"Could not read {file.path}.")
            log.write_log(log.DEBUG, err)
            data = None

        finally:
            if data:
                log.write_log(log.INFO, f"Successfully processed {file.path}.")
            return data


def sift(dir: Path, recursive=True) -> Iterator[SiftResult]:
    """Returns an iterator of filtered (sifted) audio files using a glob object.

    Can be recursive or non-recursive.
    """

    glob_pattern = str(Path("**", "*")) if recursive else "*"

    yield from [  # Yield result from glob if result is a FLAC or MPEG-4 file
        SiftResult(path=p, ftype=VALID_FILE_EXTS[p.suffix])
        for p in dir.glob(glob_pattern)
        if p.suffix in VALID_FILE_EXTS.keys()
    ]


def sift_sys() -> Iterator[SiftResult]:
    """Returns an iterator of sifted results from the entire system."""

    def get_drives() -> list[Path]:  # Helper for Windows

        ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        drives = [Path(c + ":") for c in ALPHABET if Path(c + ":").exists()]
        return drives

    USER_OS = platform.system().lower()

    # (Slightly) pesky method on Windows, iteratively sift valid drive letters
    if USER_OS in "windows" or USER_OS.startswith(("cygwin", "msys")):
        drives = get_drives()
        return chain.from_iterable(sift(Path(drive)) for drive in drives)
    
    # Much easier for UNIX-based OS: Search recursively at root directory, "/"
    elif USER_OS in "darwin" or USER_OS.startswith("linux"):
        return sift(Path("/"))
    
    # This will be expanded upon later.
    else:
        log.write_log(log.DEBUG, "Your OS is not currently supported.")
        raise SystemError


def analyze(
    log_path: Path, sifted: Iterator[SiftResult], silent=False
) -> list[MetaParams]:
    """Returns a list of MetaParams (tuple) for sifted audio files.
    
    This function spawns 2 worker processes to execute the analyze_file
    function in parallel. It also instantiates a Queue for the logging
    system to avoid corrupting the log with simultaneous I/O operations.
    """

    # Queue and listener to support concurrent logging
    log_queue = Manager().Queue(-1)

    log_listener = Process(
        target=log.listen, args=(log_queue, log_path, silent)
    )
    log_listener.start()

    results = []

    # Hardcoded 2 workers here to be safe. Will be changed in the future
    with cfutures.ProcessPoolExecutor(max_workers=2) as executor:

        # Create sequence of futures for analyze_file with sifted audio files.
        futures = {
            executor.submit(analyze_file, result, log_queue)
            for result in sifted
        }

        # Append to results if the result exists for a given file
        for future in cfutures.as_completed(futures):
            res = future.result()
            if res:
                results.append(res)

    # Ensure proper termination of the log queue with 'None'
    log_queue.put_nowait(None)

    # Terminate listener process
    log_listener.join()

    return results