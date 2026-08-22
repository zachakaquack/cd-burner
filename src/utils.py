from pathlib import Path
import shutil
import consts

import invalid_cd_fixer
from settings_manager import Settings, get_global_settings
from song_info import Song

SETTINGS: Settings = get_global_settings()


def check_requirements():
    def exists(name: str) -> bool:
        return shutil.which(f"{name}") is not None

    # cd program check
    missing_count = 0
    if not exists(consts.CDRDAO):
        missing_count += 1
    if not exists(consts.CDRECORD):
        missing_count += 1
    if not exists(consts.WODIM):
        missing_count += 1
    if missing_count == 3:
        raise ValueError(
            "Missing a CD burning program! Please install one of these: cdrdao, cdrecord, wodim"
        )

    # ensure paths are valid - do not check temporary_downloading_directory because
    # it gets created live
    if not SETTINGS.music_directory.exists():
        raise ValueError(
            "The path 'music_directory' within settings.json does not exist!"
        )
    if not SETTINGS.orpheusDL_source_directory.exists():
        raise ValueError(
            "The path 'orpheusDL_source_directory' within settings.json does not exist!"
        )
    if not SETTINGS.mpd_playlists_directory.exists():
        raise ValueError(
            "The path 'mpd_playlists_directory' within settings.json does not exist!"
        )


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
