import json
import operator
from os import system, walk  # pyright: ignore[reportDeprecated]
from pathlib import Path
from uuid import uuid4

from consts import LYRIC_FILE_EXTENSION, ORPHEUS_ALBUM_ID
from song_info import Song
import re


from settings_manager import Settings, get_global_settings
import youtube_downloader

SETTINGS: Settings = get_global_settings()


def start_downloads(link: str) -> tuple[list[Song], Path | None]:
    """
    starts the downloads and handles whether user is downloading from an orpheus compatible link
    or downloading a youtube (mainly [mai](https://www.youtube.com/@mai_dq)) playlist.
    returns a tuple of: (
    a list of Song objects
    an optional Path of the directory the music was downloaded in, to remove when finished.
    )
    """
    # example orpheus: https://music.apple.com/us/album/hornet-disaster/1786672343
    # example mai: https://youtu.be/EkFFRCS-XKo (from right click -> copy link)

    apple_match = re.match(r"(?:https?:\/\/music\.apple\.com)\/.*\/(?:\d+)", link)
    spotify_match = re.match(r"(?:https?:\/\/open\.spotify\.com)\/.+\/(?:.+)", link)
    if apple_match or spotify_match:
        return handle_orpheus_link(link)

    mai_match = re.match(r"(?:https?:\/\/youtu\.be)\/(?:.+$)", link)
    if mai_match:
        return handle_youtube_link(link), None

    raise ValueError(f"Unmatched link: {link}. Link is not valid!")


def handle_youtube_link(link: str) -> list[Song]:
    """
    downloads a video from youtube, and splits by chapter. uses the chpater info to get metadata.
    using yt-dlp
    returns a list of song objects
    """
    return youtube_downloader.start_download(link)


def handle_orpheus_link(link: str) -> tuple[list[Song], Path]:
    """
    downloads a link from something compatible with orpheus
    example: https://music.apple.com/us/album/hornet-disaster/1786672343
    returns a tuple of: (
    a list of Song objects
    the Path of the directory the music was downloaded in, to remove.
    (REMOVE PATH AFTER INSTALLING SONGS TO NOT LOSE DATA)
    )
    """

    new_download_path: Path = SETTINGS.temporary_downloading_directory / Path(
        str(uuid4())
    )
    new_download_path.mkdir()

    # FIX: horrid
    _ = system(f"""
    cd {SETTINGS.orpheusDL_source_directory} && \\
       {SETTINGS.orpheusDL_source_directory}/.venv/bin/python \\
       {SETTINGS.orpheusDL_source_directory}/orpheus.py \\
       --output "{new_download_path}" \\
       {link}
    """)

    songs: list[Song] = []
    for dir, _, files in walk(f"{new_download_path}"):
        for file in files:

            if (
                file.endswith(LYRIC_FILE_EXTENSION)
                or file == ORPHEUS_ALBUM_ID
                or file.endswith(".txt")
            ):
                continue

            full_path = Path(f"{dir}/{file}")
            songs.append(Song(full_path))

    # delete the selected directory in orpheus after installing to not clutter & waste space
    dir_to_delete: Path = Path(f"{new_download_path}")
    sorted_songs = sorted(songs, key=operator.attrgetter("tags.track_num"))
    return sorted_songs, dir_to_delete
