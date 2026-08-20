import shutil
import subprocess
import time
import operator
from os import walk
from pathlib import Path
from subprocess import run as sp_run

from song_info import Song  # pyright: ignore[reportImplicitRelativeImport]
import invalid_cd_fixer  # pyright: ignore[reportImplicitRelativeImport]
import downloading  # pyright: ignore[reportImplicitRelativeImport]

TEMPORARY_DOWNLOAD_LOCATION: Path = Path.cwd() / "downloads"
TEMPORARY_DOWNLOAD_LOCATION.mkdir(exist_ok=True)
MUSIC_DIRECTORY: Path = Path("/mnt/storage/Music/all")


def notify(title: str, body: str = "") -> None:
    args = ("notify-send", f"{title}", f"{body}")
    _ = sp_run(args)


def encode_to_flac(songs: list[Song]) -> list[Song]:
    for song in songs:
        # same thing as {song.path} but ensured to flac
        destination: Path = TEMPORARY_DOWNLOAD_LOCATION / str(song.path.stem + ".wav")
        args = (
            "ffmpeg",
            "-y",
            "-v",
            "quiet",
            "-i",
            f"{song.path}",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-f",
            "wav",
            f"{destination}",
        )
        _ = sp_run(args)
        song.path = destination  # set to new destination
    return songs


def get_songs_from_directory() -> list[Song]:
    answer: str = input("Enter path of album or path of .m3u playlist:\n> ")
    path: Path = Path(answer)
    if not path.exists():
        print(f"Path {path} is not a valid path. Try again!")
        return get_songs_from_directory()

    songs: list[Song] = []
    if path.suffix == ".m3u":
        with open(f"{path}", "r", encoding="utf-8") as playlist:
            for line in playlist:
                song_path = Path(line.strip())

                # some of my playlists are relative to MUSIC_DIRECTORY, some are absolute
                if not song_path.is_absolute():
                    # append to MUSIC_DIRECTORY (MUSIC_DIRECTORY is an absolute path)
                    song_path = MUSIC_DIRECTORY / song_path
                songs.append(Song(song_path))

        # songs are already sorted by the order of the .m3u playlist,
        # so no need to sort again here like below
        return songs

    for _, _, files in walk(f"{path}"):
        for file in files:
            if file.endswith((".lrc", ".jpg")) or file == ".orpheus_album_id":
                continue

            song_path = Path(path / file)
            songs.append(Song(song_path))

    sorted_songs = sorted(songs, key=lambda song: song.tags.track_num)
    return sorted_songs


def cue_file_error_checks(songs: list[Song]) -> list[Song]:
    # length check
    if len(songs) < 1:
        raise ValueError(
            "Error writing CUE file: length of song list is less than 1!!!!"
        )

    # check for <80min, and <700mb
    total_time: float = 0
    EIGHTY_MIN = 60 * 80

    total_bytes: int = 0
    SEVEN_HUNDRED_MEGABYTES = 700_000_000

    song_paths: list[Path] = []
    for song in songs:
        total_time += song.tags.length_seconds
        total_bytes += song.tags.file_size_bytes
        song_paths.append(song.path)

    if total_time > EIGHTY_MIN:
        return invalid_cd_fixer.fix(
            songs, invalid_cd_fixer.InvalidCDReason.Over80Minutes
        )

    if total_bytes > SEVEN_HUNDRED_MEGABYTES:
        return invalid_cd_fixer.fix(
            songs, invalid_cd_fixer.InvalidCDReason.Over700Megabytes
        )
    return songs


def construct_cue_file_2(songs: list[Song]) -> Path:

    # if no error occurs, it just returns same songs
    songs = cue_file_error_checks(songs)

    line_buffer: list[str] = []
    INDENT_1: str = "  "
    INDENT_2: str = "    "

    line_buffer.append(f'TITLE "{', '.join(songs[0].tags.album)}"')
    line_buffer.append(f'PERFORMER "mai"')

    for i, song in enumerate(songs):
        if song.path.suffix != ".wav":
            raise ValueError(f"SONG PATH IS NOT WAV!!!!")

        line_buffer.append(f'FILE "{song.path}" WAVE')
        line_buffer.append(
            f"REM FILE-DECODED-SIZE {time.strftime("%M:%S", time.gmtime(song.tags.length_seconds))}"
        )
        line_buffer.append(f"{INDENT_1}TRACK {(i + 1):02} AUDIO")
        line_buffer.append(f'{INDENT_2}TITLE "{', '.join(song.tags.title)}"')
        line_buffer.append(f'{INDENT_2}PERFORMER "{', '.join(song.tags.artist)}"')
        line_buffer.append(f"{INDENT_2}INDEX 01 00:00:00")

    CUE_PATH = TEMPORARY_DOWNLOAD_LOCATION / "album.cue"
    with open(CUE_PATH, "w", encoding="utf-8") as f:
        _ = f.write("\n".join(line_buffer))
    return CUE_PATH


# TITLE "fishmonger [Explicit]"
# PERFORMER "Underscores"
# {
# FILE "01 - 70% [Explicit].flac" FLAC
# REM FILE-DECODED-SIZE 02:40:09
#   TRACK 01 AUDIO
#     TITLE "70% [Explicit]"
#     PERFORMER "Underscores"
#     INDEX 01 00:00:00
# }...


def burn_cd(cue_path: Path) -> None:
    while True:
        output = subprocess.getoutput(("blockdev --getsize64 /dev/sr0"))
        if "medium" in output:
            print("No CD found in /dev/sr0. Enter to try again.")
            _ = input()
            continue
        break

    args = (
        "sudo",
        "cdrecord",
        "-v",
        "dev=/dev/sr0",
        "-dao",
        "-text",
        "-pad",
        "speed=16",
        f"cuefile={cue_path}",
    )
    _ = sp_run(args)


def get_song_source() -> list[Song]:

    answer = input("Are you downloading anything first? [Y]/n:\n> ")

    songs: list[Song] = []
    if not answer or answer != "n":
        songs = downloading.start_downloads()
        songs = encode_to_flac(songs)

    else:
        songs = get_songs_from_directory()
        songs = encode_to_flac(songs)

    return songs


def install_songs(songs: list[Song]) -> None:
    artist_destination: str = f"{", ".join(songs[0].tags.artist)}"
    album_destination: str = f"{", ".join(songs[0].tags.album)}"
    for song in songs:
        dest: Path = (
            MUSIC_DIRECTORY
            / f"{artist_destination}"
            / f"{album_destination}"
            / f"{song.tags.title[0]}{song.path.suffix}"
        )
        dest.parent.mkdir(exist_ok=True, parents=True)
        _ = shutil.copy(song.path, dest)


def main() -> None:
    answer = input("Are you burning a CD? [Y]/n:\n> ")
    if not answer or answer != "n":
        songs: list[Song] = get_song_source()
        cue_path: Path = construct_cue_file_2(songs)
        burn_cd(cue_path)
        return
    else:
        # just download
        songs = downloading.start_downloads()

    shutil.rmtree(TEMPORARY_DOWNLOAD_LOCATION)
    install_songs(songs)


if __name__ == "__main__":
    main()
