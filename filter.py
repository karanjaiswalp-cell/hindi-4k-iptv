import requests
import subprocess
import json
from urllib.parse import urljoin

SOURCE = "https://iptv-org.github.io/iptv/languages/hin.m3u"

OUTPUT_PLAYLIST = "Hindi-True-4K.m3u"
REPORT_FILE = "report.txt"
STATS_FILE = "stats.json"
CANDIDATES_FILE = "candidates.txt"

MIN_WIDTH = 3840
MIN_HEIGHT = 2160
MIN_BITRATE = 15000000

KEYWORDS = [
    "4k",
    "uhd",
    "2160",
    "ultra hd"
]


def get_best_hls_variant(url):
    """
    If URL is a HLS master playlist, return
    the highest-bandwidth variant stream.
    """

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

        best_bandwidth = 0
        best_url = url

        for idx, line in enumerate(lines):

            if (
                "#EXT-X-STREAM-INF" in line
                and "BANDWIDTH=" in line
            ):

                try:

                    bw = int(
                        line.split("BANDWIDTH=")[1]
                        .split(",")[0]
                    )

                    variant_url = lines[idx + 1].strip()

                    if bw > best_bandwidth:

                        best_bandwidth = bw

                        best_url = urljoin(
                            url,
                            variant_url
                        )

                except Exception:
                    pass

        return best_url

    except Exception:
        return url


print("===================================")
print("Downloading Hindi playlist...")
print("===================================")

playlist = requests.get(
    SOURCE,
    timeout=20,
    headers={
        "User-Agent": "Mozilla/5.0"
    }
).text.splitlines()

print(f"Playlist lines: {len(playlist)}")

output = ["#EXTM3U"]

report = []
candidates = []

checked = 0
passed = 0
failed = 0
candidate_count = 0

i = 0

while i < len(playlist):

    if (
        playlist[i].startswith("#EXTINF")
        and i + 1 < len(playlist)
    ):

        extinf = playlist[i]
        url = playlist[i + 1]

        if not any(
            keyword in extinf.lower()
            for keyword in KEYWORDS
        ):
            i += 2
            continue

        candidate_count += 1

        candidates.append(
            f"{extinf}\n{url}\n"
        )

        probe_url = get_best_hls_variant(url)

        checked += 1

        print(
            f"[{checked}] Checking:"
        )
        print(probe_url)

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

            if result.returncode != 0:

                failed += 1

                report.append(
                    f"{extinf}\n"
                    f"STATUS: ffprobe failed\n"
                    f"{probe_url}\n"
                )

                i += 2
                continue

            try:
                data = json.loads(
                    result.stdout
                )
            except Exception:

                failed += 1

                report.append(
                    f"{extinf}\n"
                    f"STATUS: invalid ffprobe output\n"
                    f"{probe_url}\n"
                )

                i += 2
                continue

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

            if not video_stream:

                failed += 1

                report.append(
                    f"{extinf}\n"
                    f"STATUS: no video stream\n"
                    f"{probe_url}\n"
                )

                i += 2
                continue

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

            passes_resolution = (
                width >= MIN_WIDTH
                and height >= MIN_HEIGHT
            )

            # Many IPTV providers don't expose bitrate.
            passes_bitrate = (
                bitrate == 0
                or bitrate >= MIN_BITRATE
            )

            report.append(
                f"{extinf}\n"
                f"Resolution: "
                f"{width}x{height}\n"
                f"Bitrate: {bitrate}\n"
                f"Pass Resolution: "
                f"{passes_resolution}\n"
                f"Pass Bitrate: "
                f"{passes_bitrate}\n"
                f"{probe_url}\n"
            )

            if (
                passes_resolution
                and passes_bitrate
            ):

                passed += 1

                output.extend(
                    [
                        extinf,
                        probe_url
                    ]
                )

                print(
                    f"PASS: "
                    f"{width}x{height}"
                )

            else:

                failed += 1

        except Exception as e:

            failed += 1

            report.append(
                f"{extinf}\n"
                f"ERROR: {str(e)}\n"
                f"{probe_url}\n"
            )

        i += 2

    else:
        i += 1


with open(
    OUTPUT_PLAYLIST,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "\n".join(output)
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
    CANDIDATES_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "\n\n".join(candidates)
    )

with open(
    STATS_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        {
            "candidates_found": candidate_count,
            "checked": checked,
            "passed": passed,
            "failed": failed
        },
        f,
        indent=2
    )

print()
print("===================================")
print("SUMMARY")
print("===================================")
print(f"Candidates : {candidate_count}")
print(f"Checked    : {checked}")
print(f"Passed     : {passed}")
print(f"Failed     : {failed}")
print(
    f"Playlist entries: "
    f"{(len(output)-1)//2}"
)
