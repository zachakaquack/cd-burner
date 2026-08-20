import glob
import shutil
from pathlib import Path
from mutagen.flac import FLAC
import yt_dlp
from subprocess import run as sp_run
from os import remove as os_remove, walk as os_walk
from sys import argv as sys_argv

from settings_manager import Settings, get_global_settings
from song_info import Song

SETTINGS: Settings = get_global_settings()


def start_download(url: str) -> list[Song]:
    songs: list[Song] = []

    download_video(url)
    songs = parse_songs()

    # each Song has a `.path` member var, which gets updated after this function
    encode_and_move_songs(songs)
    insert_tags(songs)
    construct_m3u(songs)

    return songs


def download_video(url: str) -> None:
    """
    downloads the video from youtube w/ yt_dlp. classic
    splits by chapter
    downloads to `SETTINGS.temporary_downloading_directory`
    """

    ydl_opts = {
        "format": "bestaudio",
        "extractaudio": True,
        "outtmpl": {
            "default": f"{SETTINGS.temporary_downloading_directory}/DELETEMEVIDEO.%(ext)s",  # unfortunately need the ext
            "chapter": f"{SETTINGS.temporary_downloading_directory}/%(section_number)02d. %(section_title)s.%(ext)s",
        },
        "quiet": False,
        "noplaylist": True,
        "postprocessors": [
            {"force_keyframes": True, "key": "FFmpegSplitChapters"},
        ],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # pyright: ignore[reportArgumentType]
        _ = ydl.download([f"{url}"])

    files = glob.glob(f"{SETTINGS.temporary_downloading_directory}/DELETEMEVIDEO*")

    # TODO: logger
    if not files:
        print(
            f"Could not find the temporary DELETEMEVIDEO to delete! check {SETTINGS.temporary_downloading_directory}"
        )

    os_remove(f"{files[0]}")
