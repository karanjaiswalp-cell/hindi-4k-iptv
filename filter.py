import requests
import json

SOURCES = [
    "https://iptv-org.github.io/iptv/languages/hin.m3u",
    "https://iptv-org.github.io/iptv/countries/in.m3u"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

HD_PLAYLIST = "Hindi-HD-Playable.m3u"
FULLHD_PLAYLIST = "Hindi-FullHD-Playable.m3u"
UHD_PLAYLIST = "Hindi-4K-Playable.m3u"

REPORT_FILE = "report.txt"
STATS_FILE = "stats.json"


def download_playlist(url):

    r = requests.get(
        url,
        timeout=20,
        headers=HEADERS
    )

    return r.text.splitlines()


def playable_stream(url):

    try:

        response = requests.get(
            url,
            timeout=5,
            headers=HEADERS,
            allow_redirects=True
        )

        if response.status_code != 200:
            return False

        text = response.text

        if "#EXTM3U" not in text:
            return False

        if (
            "#EXTINF" not in text
            and "#EXT-X-STREAM-INF" not in text
        ):
            return False

        return True

    except:
        return False


playlist = []

for source in SOURCES:

    print(
        f"Downloading {source}",
        flush=True
    )

    try:
        playlist.extend(
            download_playlist(source)
        )

    except Exception as e:

        print(
            f"Failed: {e}",
            flush=True
        )


hd = ["#EXTM3U"]
fullhd = ["#EXTM3U"]
uhd = ["#EXTM3U"]

report = []

seen = set()

checked = 0
playable = 0

hd_count = 0
fullhd_count = 0
uhd_count = 0

i = 0

while i < len(playlist):

    if (
        playlist[i].startswith("#EXTINF")
        and i + 1 < len(playlist)
    ):

        extinf = playlist[i]
        url = playlist[i + 1]

        i += 2

        if url in seen:
            continue

        seen.add(url)

        text = extinf.lower()

        quality = None

        if "(2160p)" in text:
            quality = "2160p"

        elif "(1080p)" in text:
            quality = "1080p"

        elif "(720p)" in text:
            quality = "720p"

        else:
            continue

        checked += 1

        if checked % 25 == 0:

            print(
                f"Checked {checked}",
                flush=True
            )

        if not playable_stream(url):

            report.append(
                f"FAILED | {quality} | {extinf}"
            )

            continue

        playable += 1

        if quality == "720p":

            hd.extend([
                extinf,
                url
            ])

            hd_count += 1

        elif quality == "1080p":

            hd.extend([
                extinf,
                url
            ])

            fullhd.extend([
                extinf,
                url
            ])

            hd_count += 1
            fullhd_count += 1

        elif quality == "2160p":

            hd.extend([
                extinf,
                url
            ])

            fullhd.extend([
                extinf,
                url
            ])

            uhd.extend([
                extinf,
                url
            ])

            hd_count += 1
            fullhd_count += 1
            uhd_count += 1

        report.append(
            f"OK | {quality} | {extinf}"
        )

    else:
        i += 1


with open(
    HD_PLAYLIST,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "\n".join(hd)
    )

with open(
    FULLHD_PLAYLIST,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "\n".join(fullhd)
    )

with open(
    UHD_PLAYLIST,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "\n".join(uhd)
    )

with open(
    REPORT_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "\n".join(report)
    )

with open(
    STATS_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        {
            "quality_tagged_checked": checked,
            "playable_channels": playable,
            "hd_channels": hd_count,
            "fullhd_channels": fullhd_count,
            "uhd_channels": uhd_count
        },
        f,
        indent=2
    )

print()
print("===== SUMMARY =====")
print(f"Checked   : {checked}")
print(f"Playable  : {playable}")
print(f"HD        : {hd_count}")
print(f"FullHD    : {fullhd_count}")
print(f"UHD       : {uhd_count}")
