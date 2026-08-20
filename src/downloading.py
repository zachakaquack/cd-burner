import operator
from os import system, walk  # pyright: ignore[reportDeprecated]
from pathlib import Path

from consts import LYRIC_FILE_EXTENSION, ORPHEUS_ALBUM_ID
from song_info import Song
import mai
import re


from settings_manager import Settings, get_global_settings

SETTINGS: Settings = get_global_settings()


def start_downloads() -> tuple[list[Song], Path | None]:
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

    while True:
        link = input("Enter Apple Album/Playlist ID or mai Playlist link:\n> ")

        apple_match = re.match(r"(?:https?:\/\/music\.apple\.com)\/.*\/(?:\d+)", link)
        if apple_match:
            return handle_apple_link(link)

        mai_match = re.match(r"(?:https?:\/\/youtu\.be)\/(?:.+$)", link)
        if mai_match:
            return handle_mai_link(link), None

        print("Link not recognized! Try again.")
        continue


def handle_mai_link(link: str) -> list[Song]:
    """
    downloads a [mai](https://www.youtube.com/@mai_dq) playlist
    using yt-dlp.
    returns a list of song objects
    """
    paths: list[Path] = mai.from_another_python_file(link)
    songs: list[Song] = []
    for path in paths:
        songs.append(Song(path))
    return songs


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
    ORPHEUS_DOWNLOADS_DIR = SETTINGS.orpheusDL_source_directory / "downloads"

    # FIX: horrid
    _ = system(f"""
    cd {SETTINGS.orpheusDL_source_directory} && \
    {SETTINGS.orpheusDL_source_directory}/.venv/bin/python \
    {SETTINGS.orpheusDL_source_directory}/orpheus.py \
    {link}
    """)

    # all songs are now downloaded to $HOME/Desktop/OrpheusDL/downloads
    paths: list[Path] = list(ORPHEUS_DOWNLOADS_DIR.glob("*"))
    song_dir: Path = Path()
    while True:
        for i, file in enumerate(paths):
            if file.is_file():
                continue

            string = f"'{file.stem}'"
            if i + 1 < len(paths):
                print(string, end=", ")
            else:
                print(string)

        input_answer = input("Enter name of directory that you just downloaded:\n> ")
        input_dir: Path = ORPHEUS_DOWNLOADS_DIR / Path(input_answer)
        if (
            input_answer not in ("", ".")  # ensure they typed __something__ valid
            and input_dir.exists()  # ensure is real
            and input_dir.is_dir()  # not a file (like error.txt that orpheus makes)
        ):
            song_dir = Path(input_dir)
            break
        print("Not a valid directory. Try again!")

    songs: list[Song] = []
    for dir, _, files in walk(f"{ORPHEUS_DOWNLOADS_DIR / song_dir}"):
        for file in files:

            if file.endswith(LYRIC_FILE_EXTENSION) or file == ORPHEUS_ALBUM_ID:
                continue

            full_path = Path(f"{dir}/{file}")
            songs.append(Song(full_path))

    # delete the selected directory in orpheus after installing to not clutter & waste space
    dir_to_delete: Path = Path(f"{ORPHEUS_DOWNLOADS_DIR / song_dir}")
    sorted_songs = sorted(songs, key=operator.attrgetter("tags.track_num"))
    return sorted_songs, dir_to_delete
