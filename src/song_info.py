from os import remove as os_remove
from pathlib import Path
import shutil
from typing import override
import mutagen
from os.path import getsize

from settings_manager import Settings, get_global_settings

SETTINGS: Settings = get_global_settings()


class Tags:
    """
    class that holds information about tags for Song objects.
    title: list[str] - list of titles
    artist: list[str] - list of artists
    album: list[str] - list of album names
    track_num: int - track number in album
    file_size_bytes: int - file size in bytes
    length_seconds: float - length in seconds
    """

    def __init__(
        self,
        title: list[str],
        artist: list[str],
        album: list[str],
        track_num: int,
        file_size_bytes: int,
        length_seconds: float,
    ):
        self.title: list[str] = title
        self.artist: list[str] = artist
        self.album: list[str] = album  # album or playlist
        self.track_num: int = track_num
        self.file_size_bytes: int = file_size_bytes
        self.length_seconds: float = length_seconds

    @property
    def title(self) -> list[str]:  # pyright: ignore[reportRedeclaration]
        return self._title

    @title.setter
    def title(  # pyright: ignore[reportRedeclaration]
        self, new_title: list[str]
    ) -> list[str]:
        self._title = new_title  # pyright: ignore[reportUnannotatedClassAttribute, reportUninitializedInstanceVariable]
        return self._title

    @property
    def artist(self) -> list[str]:  # pyright: ignore[reportRedeclaration]
        return self._artist

    @artist.setter
    def artist(  # pyright: ignore[reportRedeclaration]
        self, new_artist: list[str]
    ) -> list[str]:
        self._artist = new_artist  # pyright: ignore[reportUnannotatedClassAttribute, reportUninitializedInstanceVariable]
        return self._artist

    @property
    def album(self) -> list[str]:  # pyright: ignore[reportRedeclaration]
        return self._album

    @album.setter
    def album(  # pyright: ignore[reportRedeclaration]
        self, new_album: list[str]
    ) -> list[str]:
        self._album = new_album  # pyright: ignore[reportUnannotatedClassAttribute, reportUninitializedInstanceVariable]
        return self._album

    @property
    def track_num(self) -> list[str]:  # pyright: ignore[reportRedeclaration]
        return self._track_num

    @track_num.setter
    def track_num(  # pyright: ignore[reportRedeclaration]
        self, new_track_num: list[str]
    ) -> list[str]:
        self._track_num = new_track_num  # pyright: ignore[reportUnannotatedClassAttribute, reportUninitializedInstanceVariable]
        return self._track_num

    @property
    def file_size_bytes(self) -> list[str]:  # pyright: ignore[reportRedeclaration]
        return self._file_size_bytes

    @file_size_bytes.setter
    def file_size_bytes(  # pyright: ignore[reportRedeclaration]
        self, new_file_size_bytes: list[str]
    ) -> list[str]:
        self._file_size_bytes = new_file_size_bytes  # pyright: ignore[reportUnannotatedClassAttribute, reportUninitializedInstanceVariable]
        return self._file_size_bytes

    @property
    def length_seconds(self) -> list[str]:  # pyright: ignore[reportRedeclaration]
        return self._length_seconds

    @length_seconds.setter
    def length_seconds(  # pyright: ignore[reportRedeclaration]
        self, new_length_seconds: list[str]
    ) -> list[str]:
        self._length_seconds = new_length_seconds  # pyright: ignore[reportUnannotatedClassAttribute, reportUninitializedInstanceVariable]
        return self._length_seconds

    @classmethod
    def get_tags(cls, song: Song) -> Tags:
        """
        construct a Tags object from the metadata of a Song object
        """
        path: Path = song.path
        file: mutagen.FileType | None = mutagen.File(f"{path}", easy=True)
        if not file:
            raise ValueError(f"Could not identify filetype for song: {path}")

        title: list[str] = file.get("title")
        artist: list[str] = file.get("artist")
        album: list[str] = file.get("album")
        track_tag: str = file.get("track") or file.get("tracknum")
        file_size_bytes = getsize(f"{path}")
        length_seconds: float = file.info.length

        # so stupid but at this point i don't care
        if not track_tag:
            file: mutagen.FileType | None = mutagen.File(f"{path}")
            track_tag = str(file.get("trkn")[0][0])

        if len(track_tag) < 1:
            raise ValueError(f"No track num found for file: {path}")

        try:
            # this means that the first "easy" tag succeeded
            if isinstance(track_tag, list):
                track_tag = track_tag[0]

            if "/" in track_tag:
                track_num = track_tag[: track_tag.find("/") + 1]
            else:
                track_num = int(track_tag)

        except ValueError:
            raise ValueError(f"Track number is not a number!: {track_tag}")

        # ignore reportArgumentType because it will always default to ["Unknown"] otherwise
        return cls(
            title or ["Unknown"],
            artist or ["Unknown"],
            album or ["Unknown"],
            track_num or -100,
            file_size_bytes,
            length_seconds,
        )


class Song:
    """
    song object class. holds a path to its representative file and a Tags
    object to represent its metadata tags
    """

    def __init__(self, init_path: Path):

        # absolute
        self.path: Path = init_path
        self.tags: Tags = Tags.get_tags(self)

    def install_into_music_dir(self, remove_old: bool = False) -> None:
        """
        installs the song.
        changes `self.path` to the new path relative to music directory
        optionally can delete the old file (like from downloads dir)
        """

        relative = self.relative_to_music_directory()
        (SETTINGS.music_directory / relative).parent.mkdir(parents=True, exist_ok=True)

        if remove_old:
            self.path = Path(
                shutil.move(f"{self.path}", f"{SETTINGS.music_directory / relative}")
            )
        else:
            self.path = Path(
                shutil.copy(f"{self.path}", f"{SETTINGS.music_directory / relative}")
            )

    def relative_to_music_directory(self) -> Path:
        """
        construct the path relative to MUSIC_DIRECTORY in settings
        this does not return the full path. just relative to music dir.

        INABAKUMORI - Lagtrain on WEATHER STATION w/ .flac
        goes to `INABAKUMORI/WEATHER STATION/Lagtrain.flac`
        """
        artist = ", ".join(self.tags.artist)
        album = ", ".join(self.tags.album)
        title = ", ".join(self.tags.title)

        return Path(f"{artist}/{album}/{title}{self.path.suffix}")

    @property
    def path(self) -> Path:  # pyright: ignore[reportRedeclaration]
        return self._path

    @path.setter
    def path(self, new_path: Path) -> Path:  # pyright: ignore[reportRedeclaration]
        if not new_path.exists():
            raise ValueError(f"Non-existant path: {new_path}")

        if new_path.is_dir():
            raise ValueError(f"Path is a directory, not a file: {new_path}")

        self._path = new_path  # pyright: ignore[reportUnannotatedClassAttribute, reportUninitializedInstanceVariable]
        return self._path

    @override
    def __str__(self) -> str:
        return f"({self.tags.track_num}. {self.tags.album}: {self.tags.artist} - {self.tags.title} ({self.tags.length_seconds} sec, {self.tags.file_size_bytes}))"

    @override
    def __repr__(self) -> str:
        return self.__str__()
