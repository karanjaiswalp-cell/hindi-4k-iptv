import requests
import subprocess
import json
import re
from urllib.parse import urljoin

SOURCES = [
    "https://iptv-org.github.io/iptv/languages/hin.m3u",
    "https://iptv-org.github.io/iptv/countries/in.m3u"
]

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
    "ultra hd",
    "hdr"
]


def download_sources():
    merged = []

    for source in SOURCES:
        print(f"Downloading: {source}")

        try:
            lines = requests.get(
                source,
                timeout=15,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            ).text.splitlines()

            merged.extend(lines)

        except Exception as e:
            print(f"Source failed: {e}")

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

                    variant = lines[i + 1].strip()

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

        text = response.text

        matches = re.findall(
            r'RESOLUTION=(\d+)x(\d+)',
            text
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


print("Downloading playlists...")

playlist = download_sources()

print(
    f"Loaded {len(playlist)} lines"
)

output = ["#EXTM3U"]

report = []
candidates = []

checked = 0
passed = 0
failed = 0
candidate_count = 0

seen_urls = set()

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

        metadata = extinf.lower()

        if not any(
            keyword in metadata
            for keyword in KEYWORDS
        ):
            i += 2
            continue

        candidate_count += 1

        candidates.append(
            f"{extinf}\n{url}"
        )

        probe_url = get_best_hls_variant(
            url
        )

        checked += 1

        print(
            f"[{checked}] {probe_url}"
        )

        try:

            ffprobe = subprocess.run(
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

            if ffprobe.returncode == 0:

                try:

                    data = json.loads(
                        ffprobe.stdout
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

                        pass_resolution = (
                            width >= MIN_WIDTH
                            and height >= MIN_HEIGHT
                        )

                        pass_bitrate = (
                            bitrate == 0
                            or bitrate >= MIN_BITRATE
                        )

                        report.append(
                            f"{extinf}\n"
                            f"Width={width}\n"
                            f"Height={height}\n"
                            f"Bitrate={bitrate}\n"
                            f"ResolutionPass={pass_resolution}\n"
                            f"BitratePass={pass_bitrate}\n"
                            f"{probe_url}"
                        )

                        if (
                            pass_resolution
                            and pass_bitrate
                        ):

                            output.extend(
                                [
                                    extinf,
                                    probe_url
                                ]
                            )

                            passed += 1

                            i += 2
                            continue

                except Exception:
                    pass

            resolution = (
                extract_resolution_from_hls(
                    probe_url
                )
            )

            if resolution:

                width, height = resolution

                report.append(
                    f"{extinf}\n"
                    f"HLS Resolution="
                    f"{width}x{height}\n"
                    f"{probe_url}"
                )

                if (
                    width >= MIN_WIDTH
                    and height >= MIN_HEIGHT
                ):

                    output.extend(
                        [
                            extinf,
                            probe_url
                        ]
                    )

                    passed += 1

                else:
                    failed += 1

            else:

                report.append(
                    f"{extinf}\n"
                    f"STATUS=NoResolutionFound\n"
                    f"{probe_url}"
                )

                failed += 1

        except Exception as e:

            report.append(
                f"{extinf}\n"
                f"ERROR={str(e)}\n"
                f"{probe_url}"
            )

            failed += 1

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

print("========== SUMMARY ==========")
print(f"Candidates: {candidate_count}")
print(f"Checked: {checked}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
