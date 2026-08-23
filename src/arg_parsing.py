import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import override

from utils import is_valid_download_link


@dataclass
class ProgramArgs:
    source: str | Path
    device: Path
    is_simulating: bool
    is_burning_cd: bool

    @classmethod
    def load(
        cls,
        source: str | Path,
        device: Path,
        is_simulating: bool,
        is_burning_cd: bool,
    ) -> ProgramArgs:
        return cls(
            source=source,
            device=device,
            is_simulating=is_simulating,
            is_burning_cd=is_burning_cd,
        )

    @override
    def __str__(self) -> str:
        return f"{self.source = }, {self.device = }, {self.is_burning_cd = }"

    @property
    def source(self) -> str | Path:
        return self._source

    @source.setter
    def source(self, new_source: str | Path) -> str | Path:

        path: Path = Path(new_source)
        if path.exists():
            if path.is_file() and path.suffix != ".m3u":
                raise ValueError(
                    "Inputted path is a file, yet not a .m3u playlist file!"
                )

            self._source = path

            return self._source

        if is_valid_download_link(f"{new_source}"):
            self._source = new_source

            return self._source

        raise ValueError(f"Not a valid download link or path: {new_source}")

    @property
    def device(self) -> Path:
        return self._device

    @device.setter
    def device(self, new_device: Path) -> Path:
        new_device = Path(new_device)
        if not new_device.exists():
            raise ValueError(f"Path {new_device} does not exist!")
        self._device = new_device
        return self._device

    @property
    def is_simulating(self) -> bool:
        return self._is_simulating

    @is_simulating.setter
    def is_simulating(self, new_is_simulating: bool) -> bool:
        self._is_simulating = new_is_simulating
        return self._is_simulating

    @property
    def is_burning_cd(self) -> bool:
        return self._is_burning_cd

    @is_burning_cd.setter
    def is_burning_cd(self, is_burning: bool) -> bool:
        self._is_burning_cd = is_burning
        return self._is_burning_cd


def parse_args() -> ProgramArgs:
    """
    parse args :)
    input = link or dirpath or .m3u path
    defaults to burning
    python src/main.py {input}
    python src/main.py {input} --device /dev/sr0
    python src/main.py {input} --no-burn
    """

    parser = argparse.ArgumentParser(
        description="Music downloader & CD burning program."
    )
    _ = parser.add_argument(
        "source",
        help="Source of the music. Can be one of: Youtube link, a link compatible with OrpheusDL, a path to .m3u playlist, a path to directory containing music.",
    )
    _ = parser.add_argument(
        "-d",
        "--device",
        default="/dev/sr0",
        help="Device to burn cd to. Default: /dev/sr0",
    )

    _ = parser.add_argument(
        "--simulate",
        action="store_true",
        help="Like burning a CD but the laser stays cold and never writes.",
    )

    _ = parser.add_argument(
        "--no-burn",
        action="store_true",
        help="Do not burn the CD - Only download. Does nothing if provided with a local path.",
    )

    args = parser.parse_args()
    return ProgramArgs.load(
        source=args.source,
        device=args.device,
        is_simulating=args.simulate,
        is_burning_cd=not args.no_burn,
    )
