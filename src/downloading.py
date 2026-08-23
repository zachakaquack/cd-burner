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
    starts the downloads and handles whether user is downloading from apple music
    or downloading a [mai](https://www.youtube.com/@mai_dq) playlist.
    returns a tuple of: (
    a list of Song objects
    an optional Path of the directory the music was downloaded in, to remove when finished.
    )
    """
    # example apple: https://music.apple.com/us/album/hornet-disaster/1786672343
    # example mai: https://youtu.be/EkFFRCS-XKo (from right click -> copy link)

    apple_match = re.match(r"(?:https?:\/\/music\.apple\.com)\/.*\/(?:\d+)", link)
    if apple_match:
        return handle_apple_link(link)

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


def change_orpheus_download_path() -> tuple[Path, Path]:
    """
    changes the download path within orpheus' settings to an already
    known UUID, so we can avoid asking the user what they just downloaded.
    returns a path to the new downloads directory, and the UUID.
    """
    uuid_str: str = str(uuid4())
    uuid_path: Path = Path(str(uuid_str))
    new_path: Path = SETTINGS.temporary_downloading_directory / uuid_path
    orpheus_settings_path: Path = (
        SETTINGS.orpheusDL_source_directory / "config" / "settings.json"
    )
    with open(f"{orpheus_settings_path}", "r") as f:
        loaded_dict = json.load(f)  # pyright: ignore[reportAny]

    old_download_path: Path = Path(
        loaded_dict["global"]["general"]["download_path"]  # pyright: ignore[reportAny]
    )
    loaded_dict["global"]["general"]["download_path"] = f"{new_path}"

    with open(f"{orpheus_settings_path}", "w") as f:
        json.dump(loaded_dict, f)

    return (new_path, old_download_path)


def reset_orpheus_download_path(old_path: Path) -> None:
    orpheus_settings_path: Path = (
        SETTINGS.orpheusDL_source_directory / "config" / "settings.json"
    )

    with open(f"{orpheus_settings_path}", "r") as f:
        loaded_dict = json.load(f)  # pyright: ignore[reportAny]

    loaded_dict["global"]["general"]["download_path"] = f"{old_path}"

    with open(f"{orpheus_settings_path}", "w") as f:
        json.dump(loaded_dict, f)


def handle_apple_link(link: str) -> tuple[list[Song], Path]:
    """
    downloads a link from apple music.
    example: https://music.apple.com/us/album/hornet-disaster/1786672343
    returns a tuple of: (
    a list of Song objects
    the Path of the directory the music was downloaded in, to remove.
    (REMOVE PATH AFTER INSTALLING SONGS TO NOT LOSE DATA)
    )
    """

    new_download_path, old_download_path = change_orpheus_download_path()

    # FIX: horrid
    _ = system(f"""
    cd {SETTINGS.orpheusDL_source_directory} && \\
       {SETTINGS.orpheusDL_source_directory}/.venv/bin/python \\
       {SETTINGS.orpheusDL_source_directory}/orpheus.py \\
       {link}
    """)

    reset_orpheus_download_path(old_download_path)

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
