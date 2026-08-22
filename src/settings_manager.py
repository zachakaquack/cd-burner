from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass
class Settings:

    temporary_downloading_directory: Path
    """
    destination of the music after it gets downloaded, just a temporary path.
    default: CWD/downloads
    """

    music_directory: Path
    """
    destination of the music once it gets installed.
    music will get installed to `music_directory`/{artist}/{album}/{song title}.ext
    where {artist} and {album} == `", ".join(artists)` aka "Artist_1, Artist_2" etc
    default: /mnt/storage/Music/all/  (my music directory)
    """

    mpd_playlists_directory: Path
    """
    destination for .m3u playlists to end up as (when downloading from youtube)
    default: $HOME/.config/mpd/playlists
    """

    orpheusDL_source_directory: Path
    """
    directory that contains the git clone for orpheusDL. expects a setup virtual env as `.venv/`
    and the required modules downloaded.
    default: $HOME/Desktop/OrpheusDL
    """

    def __post_init__(self):
        members = [
            attr
            for attr in dir(self)
            if not callable(getattr(self, attr))  # pyright: ignore[reportAny]
            and not attr.startswith("__")
        ]
        for member in members:
            if member.endswith("_directory"):
                # sometimes, for some reason, the path is loaded as a string
                # so when you do self.path / "other_directory", it shits the bed
                # because of str / str division
                p: Path = Path(getattr(self, f"{member}"))  # pyright: ignore[reportAny]
                setattr(self, f"{member}", p)
        self.temporary_downloading_directory.mkdir(exist_ok=True)

    def write_to_disk(self) -> None:
        settings_path: Path = Path.cwd() / "settings.json"
        with open(f"{settings_path}", "w") as f:
            json.dump(self.dict(), f, indent=9)

    def dict(self) -> dict[str, str]:
        """
        convert into dictionary of str: str pairs.
        if a key ends with "_directory", then it is meant to be a Path.
        """
        # https://stackoverflow.com/a/72605423
        return {
            k: str(v) for k, v in asdict(self).items()  # pyright: ignore[reportAny]
        }

    @classmethod
    def from_dict(cls, d: dict[str, Path]) -> Settings:
        """
        return a Settings class from a dictionary
        """
        return cls(**d)

    @classmethod
    def defaults(cls) -> Settings:
        """
        return a Settings class with the default values
        """
        return Settings(
            temporary_downloading_directory=Path.cwd() / "downloads",
            music_directory=Path("/mnt/storage/Music/all"),
            mpd_playlists_directory=Path.home() / ".config/mpd/playlists",
            orpheusDL_source_directory=Path.home() / "Desktop/OrpheusDL",
        )


def _load_settings() -> Settings:
    """
    load settings from CWD / settings.json
    creates settings.json with defaults if it doesn't exist
    otherwise, just read from settings.json
        if settings.json is missing a key: value, set it as the default and read that
    """

    # the easiest thing is just doing it in the CWD, instead of worrying about where it should go
    settings_path: Path = Path.cwd() / "settings.json"
    if not settings_path.exists():
        with open(f"{settings_path}", "w") as f:
            settings = Settings.defaults()
            json.dump(settings.defaults().dict(), f, indent=9)
            return settings

    # don't you just love working with JSON?
    with open(f"{settings_path}", "r") as f:
        loaded_dict = json.load(f)  # pyright: ignore[reportAny]
        default_settings: Settings = Settings.defaults()
        members: list[str] = [
            attr
            for attr in dir(default_settings)
            if not callable(
                getattr(default_settings, attr)  # pyright: ignore[reportAny]
            )
            and not attr.startswith("__")
        ]

        # TODO: maybe implement a logger, and warn about stuff like this?

        # load the default setting if it doesn't exist
        for member in members:
            if member not in loaded_dict.keys():  # pyright: ignore[reportAny]
                key = getattr(  # pyright: ignore[reportAny]
                    default_settings, f"{member}"
                )
                loaded_dict[member] = str(key)  # pyright: ignore[reportAny]

    with open(f"{settings_path}", "w") as f:
        json.dump(loaded_dict, f, indent=9)
    return Settings.from_dict(loaded_dict)  # pyright: ignore[reportAny]


def get_global_settings() -> Settings:
    global _SETTINGS
    if "_SETTINGS" not in globals():
        _SETTINGS = _load_settings()
    return _SETTINGS
