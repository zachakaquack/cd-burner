import shutil
from os import walk
from pathlib import Path
from subprocess import run as sp_run
import sys

from cd_burning import CDBurner
from consts import LYRIC_FILE_EXTENSION, ORPHEUS_ALBUM_ID
from settings_manager import Settings, get_global_settings
from song_info import Song
import downloading
import utils
from arg_parsing import ProgramArgs, parse_args

SETTINGS: Settings = get_global_settings()
MUSIC_DIRECTORY: Path = Path("/mnt/storage/Music/all")


def encode_to_wav(songs: list[Song]) -> list[Song]:
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


def get_songs_from_directory(path: Path) -> list[Song]:
    """
    gets a song from a directory; either a .m3u file, or a directory itself.
    if user inputs a .m3u file, parse the lines and contruct a list of song objects.
    if user inputs a directory, find all music files within the specified
    directory and construct the list of song objects.
    """

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


def main() -> None:

    utils.check_requirements()

    args: ProgramArgs = parse_args(sys.argv[1:])
    songs: list[Song] = []
    cue_path: Path = Path()
    given_cue_path_already: bool = False

    if isinstance(args.source, Path):
        if args.source.suffix != ".cue":
            songs = get_songs_from_directory(args.source)
        else:
            given_cue_path_already = True
            cue_path = args.source

    else:
        songs, potential_remove = downloading.start_downloads(args.source)

        for song in songs:
            song.install_into_music_dir(remove_old=True)

        # potential_remove is the (potential) path to remove after downloading, so it doesn't bloat
        # the downloading directory from orpheus
        if potential_remove:
            shutil.rmtree(potential_remove)

    if args.is_burning_cd:
        if not given_cue_path_already:
            songs = encode_to_wav(songs)
            cue_path = utils.construct_cue_file_2(songs)
        cd_burner: CDBurner = CDBurner(device=f"{args.device}")
        cd_burner.burn_cue(cue_path, args.is_simulating)


if __name__ == "__main__":
    main()
