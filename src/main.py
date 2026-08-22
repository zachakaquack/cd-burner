import shutil
import time
from os import walk
from pathlib import Path
from subprocess import run as sp_run

from cd_burning import CDBurner
from consts import LYRIC_FILE_EXTENSION, ORPHEUS_ALBUM_ID
from settings_manager import Settings, get_global_settings
from song_info import Song
import invalid_cd_fixer
import downloading
import utils

SETTINGS: Settings = get_global_settings()
MUSIC_DIRECTORY: Path = Path("/mnt/storage/Music/all")


def encode_to_flac(songs: list[Song]) -> list[Song]:
    """
    encodes all the songs to the temporary download location,
    as .wav files
    changes the `path` member variable of each song, and just returns
    the same list of song objects
    """
    for song in songs:
        # same thing as {song.path} but ensured to flac
        destination: Path = SETTINGS.temporary_downloading_directory / str(
            song.path.stem + ".wav"
        )
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
    """
    gets a song from a directory; either a .m3u file, or a directory itself.
    if user inputs a .m3u file, parse the lines and contruct a list of song objects.
    if user inputs a directory, find all music files within the specified
    directory and construct the list of song objects.
    """
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
                    song_path = SETTINGS.music_directory / song_path
                songs.append(Song(song_path))

        # songs are already sorted by the order of the .m3u playlist,
        # so no need to sort again here like below
        return songs

    for _, _, files in walk(f"{path}"):
        for file in files:
            if (
                file.endswith((LYRIC_FILE_EXTENSION, ".jpg"))
                or file == ORPHEUS_ALBUM_ID
            ):
                continue

            song_path = Path(path / file)
            songs.append(Song(song_path))

    sorted_songs = sorted(songs, key=lambda song: song.tags.track_num)
    return sorted_songs


def cue_file_error_checks(songs: list[Song]) -> list[Song]:
    """
    does all the error checks relating to CUE files:
    1. ensure length of songs list is not 0
    2. ensure total length (time-wise) of songs is <80 minutes
    3. ensure total size of songs is <70 mb
    if an error is found, goes to `invalid_cd_fixer.fix()` and fixes the cue files
    with user interaction
    """
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
    """
    the secondcoming of the CUE construction function.
    returns a path to the CUE file that is used to burn the cd
    matches this format:

    TITLE "{album title}"
    PERFORMER "{album artist}"
    {
    FILE "{file_path.wav}" WAVE
    REM FILE-DECODED-SIZE {%M:%S}
      TRACK 01 AUDIO
        TITLE "{track title}"
        PERFORMER "{track artist}"
        INDEX 01 00:00:00
    }...
    where the ... indicates multiple tracks
    """

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

    CUE_PATH = SETTINGS.temporary_downloading_directory / "album.cue"
    with open(CUE_PATH, "w", encoding="utf-8") as f:
        _ = f.write("\n".join(line_buffer))
    return CUE_PATH


def get_song_source() -> list[Song]:
    """
    asks the user whether or not they want to download, or get from a local directory / .m3u
    encodes the songs to .wav
    returns the list of song objects
    """
    answer = input("Are you downloading anything first? [Y]/n:\n> ")

    songs: list[Song] = []
    if not answer or answer != "n":
        songs, _ = downloading.start_downloads()

    else:
        songs = get_songs_from_directory()

    songs = encode_to_flac(songs)
    return songs


def main() -> None:

    utils.check_requirements()

    answer = input("Are you burning a CD? [Y]/n:\n> ")
    if not answer or answer != "n":
        songs: list[Song] = get_song_source()
        cue_path: Path = construct_cue_file_2(songs)

        cd_burner: CDBurner = CDBurner(device="/dev/sr0")
        cd_burner.burn_cue(cue_path, simulate=True)

        return
    else:
        # just download
        songs, dir_to_delete = downloading.start_downloads()
        if dir_to_delete:
            shutil.rmtree(dir_to_delete)


if __name__ == "__main__":
    main()
