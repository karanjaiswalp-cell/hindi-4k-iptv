import requests
import json

SOURCES = [
    "https://iptv-org.github.io/iptv/languages/hin.m3u",
    "https://iptv-org.github.io/iptv/countries/in.m3u"
]

HD_PLAYLIST = "Hindi-HD-Tested.m3u"
FULLHD_PLAYLIST = "Hindi-FullHD-Tested.m3u"
UHD_PLAYLIST = "Hindi-4K-Tested.m3u"

REPORT_FILE = "report.txt"
STATS_FILE = "stats.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def playlist_lines(url):
    r = requests.get(
        url,
        timeout=20,
        headers=HEADERS
    )

    return r.text.splitlines()


def stream_alive(url):

    try:

        r = requests.get(
            url,
            timeout=5,
            headers=HEADERS,
            stream=True,
            allow_redirects=True
        )

        return r.status_code == 200

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
            playlist_lines(source)
        )
    except Exception as e:
        print(
            f"Download failed {e}",
            flush=True
        )


hd = ["#EXTM3U"]
fullhd = ["#EXTM3U"]
uhd = ["#EXTM3U"]

report = []

seen = set()

checked = 0
alive = 0

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

        checked += 1

        if checked % 50 == 0:
            print(
                f"Checked {checked}",
                flush=True
            )

        if not stream_alive(url):

            report.append(
                f"DEAD | {extinf}"
            )

            continue

        alive += 1

        text = extinf.lower()

        if "(2160p)" in text:

            uhd.extend([
                extinf,
                url
            ])

            uhd_count += 1

        elif "(1080p)" in text:

            fullhd.extend([
                extinf,
                url
            ])

            hd.extend([
                extinf,
                url
            ])

            fullhd_count += 1
            hd_count += 1

        elif "(720p)" in text:

            hd.extend([
                extinf,
                url
            ])

            hd_count += 1

        report.append(
            f"LIVE | {extinf}"
        )

    else:
        i += 1


with open(
    HD_PLAYLIST,
    "w",
    encoding="utf-8"
) as f:
    f.write("\n".join(hd))

with open(
    FULLHD_PLAYLIST,
    "w",
    encoding="utf-8"
) as f:
    f.write("\n".join(fullhd))

with open(
    UHD_PLAYLIST,
    "w",
    encoding="utf-8"
) as f:
    f.write("\n".join(uhd))

with open(
    REPORT_FILE,
    "w",
    encoding="utf-8"
) as f:
    f.write("\n".join(report))

with open(
    STATS_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        {
            "channels_checked": checked,
            "alive_channels": alive,
            "hd_channels": hd_count,
            "fullhd_channels": fullhd_count,
            "uhd_channels": uhd_count
        },
        f,
        indent=2
    )

print()
print("===== SUMMARY =====")
print(f"Checked : {checked}")
print(f"Alive   : {alive}")
print(f"HD      : {hd_count}")
print(f"FullHD  : {fullhd_count}")
print(f"UHD     : {uhd_count}")
