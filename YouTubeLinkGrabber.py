import sys
import subprocess
import json

def get_live_m3u8(target):
    """Mengambil link HLS m3u8 menggunakan yt-dlp dengan spoofing iOS Client."""
    if target.startswith("UC"):
        url = f"https://www.youtube.com/channel/{target}/live"
    elif "youtube.com" in target or "youtu.be" in target:
        url = target
    else:
        return None

    # Menggunakan client iOS / Android agar tidak terkena blokir IP Datacenter GitHub
    cmd = [
        "yt-dlp",
        "--get-url",
        "-f", "m3u8/best/b",
        "--extractor-args", "youtube:player_client=ios,android",
        "--no-warnings",
        "--geo-bypass",
        "--socket-timeout", "10",
        url
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        output = result.stdout.strip()
        if output and ("m3u8" in output or "manifest" in output):
            return output.splitlines()[0]
    except Exception as e:
        print(f"Debug Error ({target}): {e}", file=sys.stderr)
    return None

def process_target(target):
    if ".m3u8" in target and "youtube.com" not in target:
        return target
    return get_live_m3u8(target)

print("#EXTM3U")

try:
    with open("youtubeLink.txt", "r", encoding="utf-8") as f:
        raw_lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("##")]

    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        
        if "||" in line:
            parts = [p.strip() for p in line.split("||")]
            name = parts[0] if len(parts) > 0 else "Live TV"
            tvg_id = parts[1] if len(parts) > 1 else "tv.live"
            group = parts[2] if len(parts) > 2 else "General"
            
            if i + 1 < len(raw_lines):
                target_entry = raw_lines[i + 1]
                stream_url = process_target(target_entry)
                
                if stream_url:
                    print(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}" group-title="{group}", {name}')
                    print(stream_url)
                else:
                    print(f"Gagal mengambil stream: {name}", file=sys.stderr)
                
                i += 2
            else:
                i += 1
        else:
            i += 1

except Exception as e:
    print(f"Error reading youtubeLink.txt: {e}", file=sys.stderr)
