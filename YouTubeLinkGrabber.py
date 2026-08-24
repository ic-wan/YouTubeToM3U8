import sys
import subprocess

def get_yt_m3u8(url):
    cmd = [
        "yt-dlp",
        "-g",
        "-f", "best",
        "--extractor-args", "youtube:player_client=android,web",
        "--user-agent", "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        url
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
        if result.returncode == 0:
            lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            for line in lines:
                if "http" in line:
                    return line
        else:
            print(f"yt-dlp error for {url}: {result.stderr.strip()}", file=sys.stderr)
    except Exception as e:
        print(f"Exec error for {url}: {e}", file=sys.stderr)
    return None

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
                target_url = raw_lines[i + 1]
                
                # Kasus 1: Direct M3U8 Link
                if ".m3u8" in target_url and "youtube.com" not in target_url and "youtu.be" not in target_url:
                    print(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}" group-title="{group}", {name}')
                    print(target_url)
                
                # Kasus 2: YouTube Link
                else:
                    stream_url = get_yt_m3u8(target_url)
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
