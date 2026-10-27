import requests
import subprocess
import json
import re
from urllib.parse import urljoin

SOURCES = [
    "https://iptv-org.github.io/iptv/languages/hin.m3u",
    "https://iptv-org.github.io/iptv/countries/in.m3u"
]

HD_PLAYLIST = "Hindi-HD.m3u"
FULLHD_PLAYLIST = "Hindi-FullHD.m3u"

REPORT_FILE = "report.txt"
STATS_FILE = "stats.json"

MIN_HD_WIDTH = 1280
MIN_HD_HEIGHT = 720

MIN_FULLHD_WIDTH = 1920
MIN_FULLHD_HEIGHT = 1080


def download_sources():
    merged = []

    for source in SOURCES:

        print(f"Downloading: {source}")

        try:

            data = requests.get(
                source,
                timeout=15,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            merged.extend(
                data.text.splitlines()
            )

        except Exception as e:

            print(
                f"Download failed: {e}"
            )

    return merged


def get_best_hls_variant(url):

    try:

        response = requests.get(
            url,
            timeout=5,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        text = response.text

        if "#EXT-X-STREAM-INF" not in text:
            return url

        lines = text.splitlines()

        best_url = url
        best_bw = 0

        for i, line in enumerate(lines):

            if (
                "#EXT-X-STREAM-INF" in line
                and "BANDWIDTH=" in line
            ):

                try:

                    bw = int(
                        line.split(
                            "BANDWIDTH="
                        )[1].split(",")[0]
                    )

                    variant = lines[
                        i + 1
                    ].strip()

                    if bw > best_bw:

                        best_bw = bw

                        best_url = urljoin(
                            url,
                            variant
                        )

                except:
                    pass

        return best_url

    except:
        return url


def extract_resolution_from_hls(url):

    try:

        response = requests.get(
            url,
            timeout=5,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        matches = re.findall(
            r'RESOLUTION=(\d+)x(\d+)',
            response.text
        )

        if not matches:
            return None

        best = max(
            matches,
            key=lambda x: (
                int(x[0]),
                int(x[1])
            )
        )

        return (
            int(best[0]),
            int(best[1])
        )

    except:
        return None


playlist = download_sources()

print(
    f"Loaded {len(playlist)} lines"
)

hd_playlist = ["#EXTM3U"]
fullhd_playlist = ["#EXTM3U"]

report = []

checked = 0
hd_count = 0
fullhd_count = 0
failed_count = 0

seen = set()

i = 0

while i < len(playlist):

    if (
        playlist[i].startswith("#EXTINF")
        and i + 1 < len(playlist)
    ):

        extinf = playlist[i]
        url = playlist[i + 1]

        if url in seen:
            i += 2
            continue

        seen.add(url)

        checked += 1

        print(
            f"[{checked}] Checking..."
        )

        probe_url = get_best_hls_variant(
            url
        )

        width = 0
        height = 0
        bitrate = 0

        try:

            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_streams",
                    probe_url
                ],
                capture_output=True,
                text=True,
                timeout=3
            )

            if result.returncode == 0:

                data = json.loads(
                    result.stdout
                )

                video_stream = next(
                    (
                        s
                        for s in data.get(
                            "streams",
                            []
                        )
                        if s.get(
                            "codec_type"
                        ) == "video"
                    ),
                    None
                )

                if video_stream:

                    width = int(
                        video_stream.get(
                            "width",
                            0
                        )
                    )

                    height = int(
                        video_stream.get(
                            "height",
                            0
                        )
                    )

                    bitrate = int(
                        video_stream.get(
                            "bit_rate",
                            0
                        ) or 0
                    )

            if width == 0:

                resolution = (
                    extract_resolution_from_hls(
                        probe_url
                    )
                )

                if resolution:

                    width, height = (
                        resolution
                    )

        except:
            pass

        quality = "UNKNOWN"

        if (
            width >= 1920
            and height >= 1080
        ):
            quality = "1080p"

        elif (
            width >= 1280
            and height >= 720
        ):
            quality = "720p"

        elif (
            width >= 854
            and height >= 480
        ):
            quality = "480p"

        if (
            width >= MIN_HD_WIDTH
            and height >= MIN_HD_HEIGHT
        ):

            hd_playlist.extend(
                [
                    extinf,
                    probe_url
                ]
            )

            hd_count += 1

        if (
            width >= MIN_FULLHD_WIDTH
            and height >= MIN_FULLHD_HEIGHT
        ):

            fullhd_playlist.extend(
                [
                    extinf,
                    probe_url
                ]
            )

            fullhd_count += 1

        if width == 0:
            failed_count += 1

        report.append(
            f"{extinf}\n"
            f"Quality={quality}\n"
            f"Resolution={width}x{height}\n"
            f"Bitrate={bitrate}\n"
            f"{probe_url}"
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
        "\n".join(hd_playlist)
    )

with open(
    FULLHD_PLAYLIST,
    "w",
    encoding="utf-8"
) as f:
    f.write(
        "\n".join(fullhd_playlist)
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
            "failed": failed_count
        },
        f,
        indent=2
    )

print("========== SUMMARY ==========")
print(f"Checked      : {checked}")
print(f"HD           : {hd_count}")
print(f"Full HD      : {fullhd_count}")
print(f"Failed       : {failed_count}")
