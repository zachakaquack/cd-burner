import glob
from pathlib import Path
from mutagen.flac import FLAC
import yt_dlp
from subprocess import run as sp_run
from os import remove as os_remove, walk as os_walk

import consts
from settings_manager import Settings, get_global_settings
from song_info import Song

SETTINGS: Settings = get_global_settings()


def start_download(url: str) -> list[Song]:
    songs: list[Song] = []

    download_video(url)
    video_title, uploader = (
        get_the_metadata_just_for_the_title_and_uploader_of_the_playlist_lol(url)
    )

    # loops through SETTINGS.temporary_downloading_directory.
    encode_songs()

    # since these are from youtube, we have to use the chapter name to construct
    # the tags BEFORE creating the song objects (which use the metadata tags).
    # loops through SETTINGS.temporary_downloading_directory.
    insert_tags(video_title)
    songs = parse_songs()

    # each Song has a `.path` member var, which gets updated after this function
    encode_songs(songs)
    construct_m3u(songs, video_title)

    return songs


def construct_m3u(songs: list[Song], video_title: str) -> None:
    line_buffer: str = ""
    for song in songs:
        line_buffer += f"{song.path}\n"

    with open(f"{SETTINGS.mpd_playlists_directory}/{video_title}.m3u", "w") as f:
        _ = f.write(f"{line_buffer}")


def get_the_metadata_just_for_the_title_and_uploader_of_the_playlist_lol(
    url: str,
) -> tuple[str, str]:
    """
    see `get_the_metadata_just_for_the_title_and_uploader_of_the_playlist_lol()`.
    """
    ydl_opts = {
        "noplaylist": True,
        "noprogress": True,
        "quiet": True,
        "simulate": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # pyright: ignore[reportArgumentType]
        info = ydl.extract_info(url)
        return (
            info.get("title", "Unknown"),
            info.get("uploader", "Unknown"),
        )  # pyright: ignore[reportReturnType]


def insert_tags(video_title: str) -> None:
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

    for dir, _, files in os_walk(f"{SETTINGS.temporary_downloading_directory}"):
        if not files:
            continue
        files = sorted(files)
        for file in files:

            if not file.endswith(consts.FLAC_FILE_EXTENSION):
                if file.endswith(consts.WEBM_FILE_EXTENSION):
                    os_remove(f"{dir}/{file}")
                continue

            file = Path(f"{dir}/{file}")
            track_num, title, artist = find_info(f"{file.stem}{file.suffix}")

            flac = FLAC(f"{file}")
            flac["ALBUM"] = video_title
            flac["TITLE"] = title
            flac["ARTIST"] = artist
            flac["track"] = flac["track_num"] = flac["trkn"] = str(track_num)
            flac.save()  # pyright: ignore[reportUnknownMemberType]


def encode_songs() -> None:
    for dir, _, files in os_walk(f"{SETTINGS.temporary_downloading_directory}"):
        if not files:
            continue
        files = sorted(files)
        for file in files:
            file = Path(f"{dir}/{file}")
            ffmpeg_destination: Path = Path(f"{file.parent}/{file.stem}.flac")
            ffmpeg_encoding_args = (
                "ffmpeg",
                "-i",
                f"{file}",
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

            # delete old .webm (or other extension) file we encoded from
            os_remove(f"{file}")


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
