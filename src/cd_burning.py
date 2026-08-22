from pathlib import Path
import shutil
from subprocess import run as sp_run, CalledProcessError
import consts


class CDBurner:
    def __init__(self, device: str = "/dev/sr0"):
        self.device: str = device
        self._program: str = self._find_valid_program()

    def burn_cue(self, cue_path: Path, simulate: bool = False) -> None:
        """
        burn a cd using the best available tool (from `self._find_valid_program()`)
        """
        if not cue_path.exists():
            raise ValueError(f"CUE File path not found: {cue_path}")

        args: list[str] = []
        if Path(self._program).name == consts.CDRDAO:
            args = self._build_cdrdao_args(cue_path, simulate)
        else:  # elif CDRECORD or WODIM
            args = self._build_cdrecord_args(cue_path, simulate)

        try:
            _ = sp_run(args, check=True)
        except CalledProcessError as e:
            raise ValueError(f"Failed to burn cd with error e: {e}")

    def _build_cdrdao_args(self, cue_path: Path, simulate: bool) -> list[str]:
        args = ["sudo", "cdrdao"]
        args.append("simulate" if simulate else "write")

        args.extend(
            [
                "--device",
                f"{self.device}",
                "--speed",
                "16",
                "-v",
                "2",
                f"{cue_path}",
            ]
        )

        print(" ".join(args))
        return args

    def _build_cdrecord_args(self, cue_path: Path, simulate: bool) -> list[str]:
        args = ["sudo", f"{self._program}", "-v"]
        if simulate:
            args.append("-dummy")

        args.extend(
            [
                f"dev={self.device}",
                "-dao",
                "-text",
                "-pad",
                "speed=16",
                f"cuefile={cue_path}",
            ]
        )

        return args

    def _find_valid_program(self) -> str:
        """
        finds a valid program to burn the cd with. candidates are ranked in order of goodness
        """
        candidates = ["cdrdao", "cdrecord", "wodim"]
        for candidate in candidates:
            path = shutil.which(f"{candidate}")
            if path:
                return f"{candidate}"
        raise ValueError(
            f"Could not find a valid CD writing tool within these options: {", ".join(candidates)}"
        )
