import shutil
import consts

from settings_manager import Settings, get_global_settings

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
