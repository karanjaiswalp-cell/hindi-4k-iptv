import requests
import subprocess
import json

SOURCE = "https://iptv-org.github.io/iptv/languages/hin.m3u"

OUTPUT = "Hindi-True-4K.m3u"

MIN_WIDTH = 3840
MIN_HEIGHT = 2160
MIN_BITRATE = 15000000

playlist = requests.get(SOURCE, timeout=30).text.splitlines()

result = ["#EXTM3U"]

i = 0

while i < len(playlist):

    if playlist[i].startswith("#EXTINF") and i + 1 < len(playlist):

        extinf = playlist[i]
        url = playlist[i + 1]

        try:

            probe = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_streams",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            data = json.loads(probe.stdout)

            video_stream = next(
                (
                    s
                    for s in data.get("streams", [])
                    if s.get("codec_type") == "video"
                ),
                None,
            )

            if not video_stream:
                i += 2
                continue

            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))
            bitrate = int(video_stream.get("bit_rate", 0))

            if (
                width >= MIN_WIDTH
                and height >= MIN_HEIGHT
                and bitrate >= MIN_BITRATE
            ):
                result.extend([extinf, url])

        except Exception:
            pass

        i += 2

    else:
        i += 1

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write("\n".join(result))

print(f"Verified channels: {(len(result) - 1) // 2}")
