import sys
import re
import subprocess
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_video_id_from_live(channel_url):
    """Mengekstrak Video ID asli dari halaman live channel tanpa diblokir bot."""
    try:
        res = requests.get(channel_url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            # Cari video ID dari link canonical atau watch URL
            match = re.search(r'href="https://www\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})"', res.text)
            if match:
                return match.group(1)
            # Alternatif pencarian via videoId JSON key
            match_json = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', res.text)
            if match_json:
                return match_json.group(1)
    except Exception as e:
        print(f"Error resolving Video ID for {channel_url}: {e}", file=sys.stderr)
    return None

def get_yt_m3u8(target_url):
    video_url = target_url
    
    # Jika URL berupa channel /live, dapatkan Video ID spesifiknya dulu
    if "/@live" in target_url or "/live" in target_url:
        vid_id = get_video_id_from_live(target_url)
        if vid_id:
            video_url = f"https://www.youtube.com/watch?v={vid_id}"
        else:
            print(f"Gagal mengekstrak Video ID dari {target_url}", file=sys.stderr)

    cmd = [
        "yt-dlp",
        "-g",
        "-f", "b/best",
        "--extractor-args", "youtube:player_client=ios,android",
        video_url
    ]
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=25)
        if result.returncode == 0:
            lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            for line in lines:
                if "http" in line:
                    return line
        else:
            print(f"yt-dlp error [{video_url}]: {result.stderr.strip()}", file=sys.stderr)
    except Exception as e:
        print(f"Exec error [{video_url}]: {e}", file=sys.stderr)
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
                
                # Kasus 1: Link Direct M3U8
                if ".m3u8" in target_url and "youtube.com" not in target_url and "youtu.be" not in target_url:
                    print(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}" group-title="{group}", {name}')
                    print(target_url)
                
                # Kasus 2: Link YouTube
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
