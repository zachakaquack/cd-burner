from pathlib import Path

import pytest

import arg_parsing
from utils import is_valid_download_link

# TODO: unify tests to not be exclusively on my computer
DIRECTORY_TEST: str = "/mnt/storage/Music/all/Foxtails/fawn [E]/"
M3U_PLAYLIST_TEST: str = "/home/zach/.config/mpd/playlists/mai - 6c5FXD0sfKy.m3u"
ORPHEUS_TEST: str = "https://music.apple.com/us/album/hornet-disaster/1786672343"
YOUTUBE_TEST: str = "https://youtu.be/EkFFRCS-XKo"

ALL_TESTS: list[str] = [
    DIRECTORY_TEST,
    M3U_PLAYLIST_TEST,
    ORPHEUS_TEST,
    YOUTUBE_TEST,
]


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


def test_inputs_default() -> None:
    expected: arg_parsing.ProgramArgs = arg_parsing.ProgramArgs(
        source=DIRECTORY_TEST,
        device=Path("/dev/sr0"),
        is_burning_cd=True,
        is_simulating=False,
    )
    for test in ALL_TESTS:
        expected.source = test
        args: arg_parsing.ProgramArgs = arg_parsing.parse_args([test])
        assert_args_correct(args, expected)


def test_inputs_no_burn() -> None:
    expected: arg_parsing.ProgramArgs = arg_parsing.ProgramArgs(
        source=DIRECTORY_TEST,
        device=Path("/dev/sr0"),
        is_burning_cd=False,
        is_simulating=False,
    )
    for test in ALL_TESTS:
        expected.source = test
        args: arg_parsing.ProgramArgs = arg_parsing.parse_args([test, "--no-burn"])
        assert_args_correct(args, expected)


def test_inputs_simulate() -> None:
    expected: arg_parsing.ProgramArgs = arg_parsing.ProgramArgs(
        source=DIRECTORY_TEST,
        device=Path("/dev/sr0"),
        is_burning_cd=True,
        is_simulating=True,
    )
    for test in ALL_TESTS:
        expected.source = test
        args: arg_parsing.ProgramArgs = arg_parsing.parse_args([test, "--simulate"])
        assert_args_correct(args, expected)


def test_inputs_custom_device() -> None:
    # the only check on the device is if it exists
    device: Path = Path.cwd()

    expected: arg_parsing.ProgramArgs = arg_parsing.ProgramArgs(
        source=DIRECTORY_TEST,
        device=device,
        is_burning_cd=True,
        is_simulating=False,
    )
    for test in ALL_TESTS:
        expected.source = test
        args: arg_parsing.ProgramArgs = arg_parsing.parse_args(
            [test, f"--device={device}"]
        )
        assert_args_correct(args, expected)


def test_inputs_no_burn_simulate() -> None:
    expected: arg_parsing.ProgramArgs = arg_parsing.ProgramArgs(
        source=DIRECTORY_TEST,
        device=Path("/dev/sr0"),
        is_burning_cd=False,
        is_simulating=True,
    )
    for test in ALL_TESTS:
        expected.source = test
        args: arg_parsing.ProgramArgs = arg_parsing.parse_args(
            [test, "--no-burn", "--simulate"]
        )
        assert_args_correct(args, expected)


def test_inputs_default_invalid_m3u_source() -> None:
    with pytest.raises(ValueError):
        _: arg_parsing.ProgramArgs = arg_parsing.parse_args(
            [
                str(Path().cwd() / "README.md"),
            ]
        )


def test_inputs_default_invalid_device() -> None:
    with pytest.raises(ValueError):
        _: arg_parsing.ProgramArgs = arg_parsing.parse_args(
            [ALL_TESTS[0], f"--device={str(Path().cwd() / "notexistant")}"]
        )
