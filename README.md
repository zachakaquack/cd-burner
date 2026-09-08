# cd-burner

## cli program to burn cds.

basically a wrapper around cdrdao and orpheusdl.
will also "install" songs into a predetermined music directory (MUSIC_DIR/{artist}/{album}/{song[s]}), and embed metadata tags if needed.

only downloads from spotify & apple music because thats all i check for.
if you want to ignore that, edit the `start_downloads()` function in `src/downloading.py` and the `is_valid_download_link()` check in `src/arg_parsing.py`

## requirements:

1.  cdrdao or an equivalant (cdrdao, cdrecord, wodim)
2.  [OrpheusDL](https://github.com/bascurtiz/OrpheusDL)
3.  yt-dlp

## usage:

```
python src/main.py [-h] [-d DEVICE] [--simulate] [--no-burn] source

# burn a cd, downloading from apple music
python src/main.py https://music.apple.com/us/album/b4-the-world-single/6803743105

# burn a cd, from a local playlist / directory
python src/main.py --no-burn /path/to/directory/of/files
python src/main.py --no-burn /path/to/playlist.m3u

# only download and install songs, do not burn
python src/main.py --no-burn https://music.apple.com/us/album/b4-the-world-single/6803743105
```
