from pathlib import Path

import pytest

import arg_parsing
from utils import is_valid_download_link


@pytest.fixture()
def dummy_sources(
    dummy_album_path, dummy_m3u_path, dummy_orpheus, dummy_youtube
) -> list[str]:
    return [
        f"{dummy_album_path}",
        f"{dummy_m3u_path}",
        f"{dummy_orpheus}",
        f"{dummy_youtube}",
    ]


@pytest.fixture()
def dummy_orpheus() -> str:
    return "https://music.apple.com/us/album/hornet-disaster/1786672343"


@pytest.fixture()
def dummy_youtube() -> str:
    return "https://youtu.be/EkFFRCS-XKo"


@pytest.fixture
def dummy_album_path(tmp_path: Path) -> Path:
    # good album yo
    album_dir: Path = (
        tmp_path / "MASS OF THE FERMENTING DREGS" / "Zero Comma Iro Toridori no Sekai"
    )
    album_dir.mkdir(parents=True)

    for i in range(1, 5):
        song_path: Path = album_dir / f"{i:02d}. Song {i}.flac"
        _ = song_path.write_bytes(b"DUMMY_FLAC")

    return album_dir


@pytest.fixture
def dummy_m3u_path(tmp_path: Path, dummy_album_path: Path) -> Path:
    m3u_file: Path = tmp_path / "test_playlist.m3u"
    tracks: list[Path] = list(dummy_album_path.glob("*.flac"))
    tracks.sort()

    lines: list[str] = []
    for track in tracks:
        lines.append(f"{track.resolve()}")

    with open(f"{m3u_file}", "w") as f:
        _ = f.write("\n".join(lines))

    return m3u_file


def source_is_valid(source: str | Path) -> bool:
    if isinstance(source, Path):
        if source.exists():
            return True
    else:
        return is_valid_download_link(source)
    return False


def assert_args_correct(
    program_args: arg_parsing.ProgramArgs, expected: arg_parsing.ProgramArgs
) -> None:
    assert source_is_valid(program_args.source)
    assert program_args.device == expected.device
    assert program_args.is_burning_cd == expected.is_burning_cd
    assert program_args.is_simulating == expected.is_simulating


def test_inputs_default(dummy_sources) -> None:
    expected: arg_parsing.ProgramArgs = arg_parsing.ProgramArgs(
        source=dummy_sources[0],
        device=Path("/dev/sr0"),
        is_burning_cd=True,
        is_simulating=False,
    )
    for test in dummy_sources:
        expected.source = test
        args: arg_parsing.ProgramArgs = arg_parsing.parse_args([f"{test}"])
        assert_args_correct(args, expected)


def test_inputs_no_burn(dummy_sources) -> None:
    expected: arg_parsing.ProgramArgs = arg_parsing.ProgramArgs(
        source=dummy_sources[0],
        device=Path("/dev/sr0"),
        is_burning_cd=False,
        is_simulating=False,
    )
    for test in dummy_sources:
        expected.source = test
        args: arg_parsing.ProgramArgs = arg_parsing.parse_args([f"{test}", "--no-burn"])
        assert_args_correct(args, expected)


def test_inputs_simulate(dummy_sources) -> None:
    expected: arg_parsing.ProgramArgs = arg_parsing.ProgramArgs(
        source=dummy_sources[0],
        device=Path("/dev/sr0"),
        is_burning_cd=True,
        is_simulating=True,
    )
    for test in dummy_sources:
        expected.source = test
        args: arg_parsing.ProgramArgs = arg_parsing.parse_args(
            [f"{test}", "--simulate"]
        )
        assert_args_correct(args, expected)


def test_inputs_custom_device(dummy_sources) -> None:
    # the only check on the device is if it exists
    device: Path = Path.cwd()

    expected: arg_parsing.ProgramArgs = arg_parsing.ProgramArgs(
        source=dummy_sources[0],
        device=device,
        is_burning_cd=True,
        is_simulating=False,
    )

    for test in dummy_sources:
        expected.source = test
        args: arg_parsing.ProgramArgs = arg_parsing.parse_args(
            [f"{test}", f"--device={device}"]
        )
        assert_args_correct(args, expected)


def test_inputs_no_burn_simulate(dummy_sources) -> None:
    expected: arg_parsing.ProgramArgs = arg_parsing.ProgramArgs(
        source=dummy_sources[0],
        device=Path("/dev/sr0"),
        is_burning_cd=False,
        is_simulating=True,
    )
    for test in dummy_sources:
        expected.source = test
        args: arg_parsing.ProgramArgs = arg_parsing.parse_args(
            [f"{test}", "--no-burn", "--simulate"]
        )
        assert_args_correct(args, expected)


def test_inputs_invalid_m3u_source() -> None:
    with pytest.raises(ValueError):
        _: arg_parsing.ProgramArgs = arg_parsing.parse_args(
            [
                str(Path().cwd() / "README.md"),
            ]
        )


def test_inputs_invalid_device(dummy_album_path) -> None:
    with pytest.raises(ValueError):
        _: arg_parsing.ProgramArgs = arg_parsing.parse_args(
            [f"{dummy_album_path}", f"--device={str(Path().cwd() / "notexistant")}"]
        )
