import sys
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

# Node API Piped & Invidious Publik (Bypass Blokir IP Datacenter GitHub)
PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://api.piped.privacydev.net",
    "https://pipedapi.drg.ng"
]

INVIDIOUS_INSTANCES = [
    "https://inv.tux.pizza",
    "https://invidious.nerdvpn.de",
    "https://vid.puffyan.us"
]

def get_live_stream_from_piped(channel_id):
    """Mendapatkan link stream HLS m3u8 langsung via Piped API."""
    for instance in PIPED_INSTANCES:
        try:
            # Fetch detail channel
            c_url = f"{instance}/channel/{channel_id}"
            res = requests.get(c_url, headers=HEADERS, timeout=6)
            if res.status_code == 200:
                data = res.json()
                related_streams = data.get("relatedStreams", [])
                
                # Cari stream yang berstatus LIVE
                live_video_id = None
                for stream in related_streams:
                    if stream.get("isLive", False):
                        live_video_id = stream.get("url", "").replace("/watch?v=", "")
                        break
                
                # Jika ditemukan video live, ambil manifest hls-nya
                if live_video_id:
                    v_url = f"{instance}/streams/{live_video_id}"
                    v_res = requests.get(v_url, headers=HEADERS, timeout=6)
                    if v_res.status_code == 200:
                        v_data = v_res.json()
                        hls_url = v_data.get("hls")
                        if hls_url:
                            return hls_url
        except Exception:
            continue
    return None

def get_live_stream_from_invidious(channel_id):
    """Fallback ke Invidious API jika Piped API tidak merespons."""
    for instance in INVIDIOUS_INSTANCES:
        try:
            url = f"{instance}/api/v1/channels/{channel_id}/videos"
            res = requests.get(url, headers=HEADERS, timeout=6)
            if res.status_code == 200:
                videos = res.json().get("videos", [])
                for v in videos:
                    # Filter khusus video siaran langsung
                    if v.get("isLive", False):
                        video_id = v.get("videoId")
                        v_info = requests.get(f"{instance}/api/v1/videos/{video_id}", timeout=6).json()
                        hls_url = v_info.get("hlsUrl")
                        if hls_url:
                            return hls_url
        except Exception:
            continue
    return None

def process_target(target):
    # Jika URL langsung berupa .m3u8
    if ".m3u8" in target and "youtube.com" not in target:
        return target

    if target.startswith("UC"):
        # Prioritas 1: Piped API
        hls_url = get_live_stream_from_piped(target)
        if hls_url:
            return hls_url
            
        # Prioritas 2: Invidious API Fallback
        hls_url = get_live_stream_from_invidious(target)
        if hls_url:
            return hls_url

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
