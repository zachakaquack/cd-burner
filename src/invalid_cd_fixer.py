from enum import Enum
import time

from song_info import Song


class InvalidCDReason(Enum):
    Over80Minutes = 0
    Over700Megabytes = 1


def invalid_cd_reason_to_string(reason: InvalidCDReason) -> str:
    match reason:
        case InvalidCDReason.Over80Minutes:
            return "CD Length is over 80 minutes!"
        case InvalidCDReason.Over700Megabytes:
            return "CD Length is over 700 Megabytes!"


def fix(songs: list[Song], reason: InvalidCDReason) -> list[Song]:
    print(
        f"Error found while constructing CD! Reason: {invalid_cd_reason_to_string(reason)}"
    )
    match reason:
        case InvalidCDReason.Over80Minutes:
            return handle_too_long(songs)
        case InvalidCDReason.Over700Megabytes:
            raise NotImplemented


def handle_too_long(songs: list[Song]) -> list[Song]:
    edited_songs: list[Song] = songs
    while True:
        total_seconds: float = 0
        last_valid_song_found: bool = False
        for i, song in enumerate(edited_songs):
            total_seconds += song.tags.length_seconds
            single_formatted = time.strftime(
                "%M:%S", time.gmtime(song.tags.length_seconds)
            )
            total_formatted = time.strftime("%H:%M:%S", time.gmtime(total_seconds))

            message = f"{i:02}. {', '.join(song.tags.title)}: +{single_formatted} - {total_formatted}"
            if i + 1 < len(edited_songs) and not last_valid_song_found:
                new_total: float = (
                    total_seconds + edited_songs[i + 1].tags.length_seconds
                )
                if new_total > 80 * 60:
                    print(f"{message} <----------- Last Valid Song")
                    last_valid_song_found = True
                    continue

            print(message)

        total_formatted = time.strftime("%H:%M:%S", time.gmtime(total_seconds))
        print(f"Total Time: {total_formatted}")

        if total_seconds < 80 * 60:
            print("Done!")
            return edited_songs

        answer = input("Enter track number to delete:\n> ")
        index: int = -1
        try:
            index = int(answer)
        except ValueError:
            print("Not a number! Try again.")
        if index < 0 or index >= len(edited_songs):
            print("Out of bounds! Try again.")

        print(f"Deleting {index}. {", ".join(edited_songs[index].tags.title)}...\n")
        _ = edited_songs.pop(index)


def handle_too_big(songs: list[Song]) -> list[Song]:
    edited_songs: list[Song] = songs
    while True:
        total_megabytes: float = 0
        last_valid_song_found: bool = False
        for i, song in enumerate(edited_songs):
            total_megabytes += song.tags.file_size_bytes
            single_formatted = song.tags.file_size_bytes // 1000
            total_formatted = total_megabytes // 1000

            message = f"{i:02}. {', '.join(song.tags.title)}: +{single_formatted} - {total_formatted}"
            if i + 1 < len(edited_songs) and not last_valid_song_found:
                new_total: float = (
                    total_megabytes + edited_songs[i + 1].tags.length_seconds
                )
                if new_total > 700_000_000:
                    print(f"{message} <----------- Last Valid Song")
                    last_valid_song_found = True
                    continue

            print(message)

        total_formatted = total_megabytes // 1000
        print(f"Total MB: {total_formatted}")

        if total_megabytes < 700_000_000:
            print("Done!")
            return edited_songs

        answer = input("Enter track number to delete:\n> ")
        index: int = -1
        try:
            index = int(answer)
        except ValueError:
            print("Not a number! Try again.")
        if index < 0 or index >= len(edited_songs):
            print("Out of bounds! Try again.")

        print(f"Deleting {index}. {", ".join(edited_songs[index].tags.title)}...\n")
        _ = edited_songs.pop(index)
