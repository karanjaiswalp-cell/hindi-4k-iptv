import requests
import json

SOURCES = [
    "https://iptv-org.github.io/iptv/languages/hin.m3u",
    "https://iptv-org.github.io/iptv/countries/in.m3u"
]

HD_PLAYLIST = "Hindi-HD.m3u"
FULLHD_PLAYLIST = "Hindi-FullHD.m3u"
UHD_PLAYLIST = "Hindi-4K.m3u"

REPORT_FILE = "report.txt"
STATS_FILE = "stats.json"


def download_playlist(url):

    print(f"Downloading: {url}", flush=True)

    response = requests.get(
        url,
        timeout=20,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    return response.text.splitlines()


playlist = []

for source in SOURCES:
    try:
        playlist.extend(
            download_playlist(source)
        )
    except Exception as e:
        print(
            f"Failed: {source} : {e}",
            flush=True
        )

print(
    f"Loaded {len(playlist)} lines",
    flush=True
)

hd = ["#EXTM3U"]
fullhd = ["#EXTM3U"]
uhd = ["#EXTM3U"]

report = []

seen_urls = set()

checked = 0
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

        if url in seen_urls:
            i += 2
            continue

        seen_urls.add(url)

        checked += 1

        quality = "UNKNOWN"

        text = extinf.lower()

        if "(2160p)" in text:

            quality = "2160p"

            uhd.extend([
                extinf,
                url
            ])

            uhd_count += 1

        elif "(1080p)" in text:

            quality = "1080p"

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

            quality = "720p"

            hd.extend([
                extinf,
                url
            ])

            hd_count += 1

        report.append(
            f"{quality} | {extinf}\n{url}"
        )

        if checked % 100 == 0:

            print(
                f"Checked {checked} channels",
                flush=True
            )

        i += 2

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
        "\n\n".join(report)
    )

with open(
    STATS_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        {
            "channels_checked": checked,
            "hd_channels": hd_count,
            "fullhd_channels": fullhd_count,
            "uhd_channels": uhd_count
        },
        f,
        indent=2
    )

print()
print("===== SUMMARY =====")
print(f"Checked  : {checked}")
print(f"HD       : {hd_count}")
print(f"Full HD  : {fullhd_count}")
print(f"UHD      : {uhd_count}")
