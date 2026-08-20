import glob
import shutil
from pathlib import Path
from mutagen.flac import FLAC
import yt_dlp
from subprocess import run as sp_run
from os import remove as os_remove, walk as os_walk
from sys import argv as sys_argv

TEST_URL = "https://www.youtube.com/watch?v=EkFFRCS-XKo&list=RDEkFFRCS-XKo&start_radio=1&t=771s"
TEMP_DOWNLOAD_PATH = Path.cwd() / "downloads"
FINAL_DOWNLOAD_PATH = Path("/mnt/storage/Music/all")

TEMP_DOWNLOAD_PATH.mkdir(exist_ok=True)
FINAL_DOWNLOAD_PATH.mkdir(exist_ok=True)


def notify(title: str, body: str = "") -> None:
    args = ("notify-send", f"{title}", f"{body}")
    _ = sp_run(args)


def download_video(url: str) -> None:

    ydl_opts = {
        "format": "bestaudio",
        "extractaudio": True,
        "outtmpl": {
            "default": f"{TEMP_DOWNLOAD_PATH}/DELETEMEVIDEO.%(ext)s",  # unfortunately need the ext
            "chapter": f"{TEMP_DOWNLOAD_PATH}/%(section_number)02d. %(section_title)s.%(ext)s",
        },
        "quiet": False,
        "noplaylist": True,
        "postprocessors": [
            # # better encoding of the chapter timings
            {"force_keyframes": True, "key": "FFmpegSplitChapters"},
        ],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # pyright: ignore[reportArgumentType]
        _ = ydl.download([f"{url}"])

    files = glob.glob(f"{TEMP_DOWNLOAD_PATH}/DELETEMEVIDEO*")
    if not files:
        notify(
            "TEMPORARY DOWNLOAD NOT FOUND!",
            "the temporary DELETEMEVIDEO file was not found!",
        )
        return

    os_remove(f"{files[0]}")


# gets track_num, artist, title from the filename
def find_info(filename: str) -> tuple[int, str, str]:
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


def reencode_the_fuckers() -> None:
    for _, _, files in os_walk(f"{TEMP_DOWNLOAD_PATH}"):
        if not files:
            continue
        files = sorted(files)

        for file in files:
            if file.endswith(".cue"):
                continue
            file = Path(file)
            # ffmpeg -i {FILE} -sample_fmt s16 -ar 48000 -map_metadata 0:s:a:0 -c:a flac {output}
            args = (
                "ffmpeg",
                "-i",
                f"{TEMP_DOWNLOAD_PATH}/{file}",
                "-sample_fmt",
                "s16",
                "-ar",
                "48000",
                "-map_metadata",
                "0:",
                "-c:a",
                "flac",
                f"{TEMP_DOWNLOAD_PATH}/{file.stem}.flac",
            )
            _ = sp_run(args)
            os_remove(f"{TEMP_DOWNLOAD_PATH}/{file}")


def get_the_metadata_just_for_the_title_of_the_playlist_lol(url: str) -> str:

    ydl_opts = {
        "noplaylist": True,
        "noprogress": True,
        "quiet": True,
        "simulate": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # pyright: ignore[reportArgumentType]
        info = ydl.extract_info(url)
        return info.get("title", "Unknown")  # pyright: ignore[reportReturnType]


def main(url: str = "") -> Path:

    if not url:
        args = sys_argv
        if len(args) == 1:
            print("usecase: python ./main.py {YOUTUBE_URL}")
            exit()
        url = str(args[1])

    download_video(url)

    # i am very mad grrr
    reencode_the_fuckers()

    playlist_title = get_the_metadata_just_for_the_title_of_the_playlist_lol(url)
    mpd_playlist: Path = (
        Path().home() / ".config/mpd/playlists" / f"mai - {playlist_title}.m3u"
    )

    # list of files relative to FINAL_DOWNLOAD_PATH for the mpd playlist
    playlist_files: list[Path] = []

    # big programming doesnt wan't you to know you can do things without making them into functions
    for _, _, files in os_walk(f"{TEMP_DOWNLOAD_PATH}"):
        if not files:
            continue
        files = sorted(files)

        for file in files:
            track, artist, title = find_info(filename=file)

            flac = FLAC(f"{TEMP_DOWNLOAD_PATH}/{file}")
            flac["ALBUM"] = playlist_title
            flac["TITLE"] = title
            flac["ARTIST"] = artist
            flac["track"] = flac["track_num"] = str(track)
            flac.save()  # pyright: ignore[reportUnknownMemberType]

            src = f"{TEMP_DOWNLOAD_PATH}/{file}"
            dest: Path = Path(f"{FINAL_DOWNLOAD_PATH}/{artist}/Unknown/{title}.flac")
            dest.parent.mkdir(parents=True, exist_ok=True)
            _ = shutil.move(src, dest)

            playlist_files.append(dest)

    # construct playlist file @ $HOME/.config/mpd/playlists/mai - {mpd_playlist}.m3u
    with open(f"{mpd_playlist}", "w") as f:
        _ = f.write("\n".join(map(str, playlist_files)))

    notify("done fucko", f"finished: {playlist_title}")
    return mpd_playlist


# return a list of Paths for a list of Songs
def from_another_python_file(url: str) -> list[Path]:
    mpd_playlist: Path = main(url=url)
    songs: list[Path] = []
    with open(f"{mpd_playlist}", "r", encoding="utf-8") as playlist:
        for line in playlist:
            song_path = Path(line.strip())
            songs.append(song_path)

    # songs are already sorted by the order of the .m3u playlist,
    # so no need to sort again here like below
    return songs


if __name__ == "__main__":
    _ = main()
