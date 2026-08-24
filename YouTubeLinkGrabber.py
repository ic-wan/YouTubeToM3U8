import sys
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
}

# Daftar instance Invidious publik sebagai mirror YouTube
INVIDIOUS_INSTANCES = [
    "https://inv.tux.pizza",
    "https://invidious.nerdvpn.de",
    "https://inv.hostux.net",
    "https://yewtu.be",
    "https://invidious.drgns.space"
]

def get_hls_from_invidious(target):
    """Mengambil m3u8 stream dari Invidious API untuk menghindari IP block GitHub Actions."""
    channel_id = target.strip()
    
    # Resolusi jika input berupa URL watch
    if "watch?v=" in target:
        video_id = target.split("watch?v=")[1].split("&")[0]
        for instance in INVIDIOUS_INSTANCES:
            try:
                url = f"{instance}/api/v1/videos/{video_id}"
                res = requests.get(url, headers=HEADERS, timeout=6)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("hlsUrl"):
                        return data["hlsUrl"]
            except Exception:
                continue
        return None

    # Jika target berupa Channel ID (UC...) atau Handle (@...)
    for instance in INVIDIOUS_INSTANCES:
        try:
            # 1. Ambil daftar video terbaru dari channel
            url = f"{instance}/api/v1/channels/{channel_id}"
            res = requests.get(url, headers=HEADERS, timeout=6)
            if res.status_code != 200:
                continue

            data = res.json()
            latest_videos = data.get("latestVideos", [])

            # Cari video yang sedang statusnya 'isLive'
            live_video_id = None
            for vid in latest_videos:
                if vid.get("isLive", False):
                    live_video_id = vid.get("videoId")
                    break

            # Jika tidak ada flag isLive, ambil video paling pertama (terbaru)
            if not live_video_id and latest_videos:
                live_video_id = latest_videos[0].get("videoId")

            if live_video_id:
                # 2. Ambil detail HLS m3u8 dari video_id tersebut
                vid_url = f"{instance}/api/v1/videos/{live_video_id}"
                vid_res = requests.get(vid_url, headers=HEADERS, timeout=6)
                if vid_res.status_code == 200:
                    vid_data = vid_res.json()
                    if vid_data.get("hlsUrl"):
                        return vid_data["hlsUrl"]
        except Exception:
            continue

    return None

def process_target(target):
    if ".m3u8" in target and "youtube.com" not in target:
        return target
    return get_hls_from_invidious(target)

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
