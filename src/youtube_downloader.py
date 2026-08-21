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
    video_title = get_the_metadata_just_for_the_title_of_the_playlist_lol(url)

    # since these are from youtube, we have to use the chapter name to construct
    # the tags BEFORE creating the song objects (which use the metadata tags).
    insert_tags(songs, video_title)
    songs = parse_songs()

    # each Song has a `.path` member var, which gets updated after this function
    encode_songs(songs)

    return songs


def get_the_metadata_just_for_the_title_of_the_playlist_lol(url: str) -> str:
    """
    see `get_the_metadata_just_for_the_title_of_the_playlist_lol()`.
    """
    ydl_opts = {
        "noplaylist": True,
        "noprogress": True,
        "quiet": True,
        "simulate": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # pyright: ignore[reportArgumentType]
        info = ydl.extract_info(url)
        return info.get("title", "Unknown")  # pyright: ignore[reportReturnType]


def insert_tags(songs: list[Song], video_title: str) -> None:
    def find_info(filename: str) -> tuple[int, str, str]:
        """
        gets the information from the filename.
        return a tuple of: (
            track_num: int,
            title: str,
            artist: str,
        )
        inputted filename should look like: "%(section_number)02d. %(section_title)s.%(ext)s"
        e.g. "05. My Super Awesome Song Name - Your Epic Artist Name.extension"
        (the title & artist are both in the section title)
        """
        track_num: int = 0
        artist: str = ""
        title: str = ""

        track_num = int(
            filename[:2]
        )  # 2 because track_num is formatted as DD. where D is a digit
        filename = filename[4:]  # 4 because the first 4 chars are always "DD. "

        # artist is first; and in the weird case of Midsummer - Flamingosis (Ehted kadunud - Collage),
        # title is Midsummer and artist is Flamingosis... so only break once
        title, artist = filename.split(" - ", maxsplit=1)

        # artist is now "{ARTIST}.extension" :(
        artist = artist[: artist.rfind(".")]

        return (track_num, artist, title)

    for song in songs:
        track_num, title, artist = find_info(song.path.stem)

        flac = FLAC(f"{song.path}")
        flac["ALBUM"] = video_title
        flac["TITLE"] = title
        flac["ARTIST"] = artist
        flac["track"] = flac["track_num"] = flac["trkn"] = str(track_num)
        flac.save()  # pyright: ignore[reportUnknownMemberType]


def encode_songs(songs: list[Song]) -> None:
    for song in songs:
        ffmpeg_destination: Path = Path(f"{song.path.parent}/{song.path.stem}.flac")
        ffmpeg_encoding_args = (
            "ffmpeg",
            "-i",
            f"{song.path}",
            "-sample_fmt",
            "s16",
            "-ar",
            "48000",
            "-map_metadata",
            "0:",
            "-c:a",
            "flac",
            # /dir/song.mp3 -> /dir/song.flac
            f"{ffmpeg_destination}",
        )
        _ = sp_run(ffmpeg_encoding_args)
        song.path = ffmpeg_destination

        # delete old
        old_path: Path = song.path
        os_remove(f"{old_path}")


def parse_songs() -> list[Song]:
    songs: list[Song] = []
    for dir, _, files in os_walk(f"{SETTINGS.temporary_downloading_directory}"):
        if not files:
            continue

        for file in files:
            full_path = Path(f"{dir}") / f"{file}"
            songs.append(Song(init_path=full_path))

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
