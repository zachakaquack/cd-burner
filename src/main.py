import shutil
import time
from os import walk
from pathlib import Path
from subprocess import run as sp_run

from cd_burning import CDBurner
from consts import LYRIC_FILE_EXTENSION, ORPHEUS_ALBUM_ID
from settings_manager import Settings, edit_settings, get_global_settings
from song_info import Song
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
    if not (Path.cwd() / "settings.json").exists():
        edit_settings()

    answer = input("Are you burning a CD? [Y]/n:\n> ")
    if not answer or answer != "n":
        songs: list[Song] = get_song_source()
        cue_path: Path = utils.construct_cue_file_2(songs)

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
