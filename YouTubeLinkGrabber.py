import sys
import json
import subprocess
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}

# Mirror API publik yang stabil di runner CI/CD
PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://api.piped.privacydev.net",
    "https://pipedapi.mha.fi",
    "https://piped-api.garudalinux.org"
]

INVIDIOUS_INSTANCES = [
    "https://inv.tux.pizza",
    "https://invidious.nerdvpn.de",
    "https://yewtu.be"
]

def get_hls_via_piped(target):
    """Mencari stream HLS via Piped API."""
    for instance in PIPED_INSTANCES:
        try:
            # 1. Ambil video live dari channel
            url = f"{instance}/channel/{target}"
            res = requests.get(url, headers=HEADERS, timeout=5)
            if res.status_code == 200:
                data = res.json()
                related = data.get("relatedStreams", [])
                live_video_id = None
                for vid in related:
                    if vid.get("isStream", False) or vid.get("type") == "stream":
                        live_video_id = vid.get("url", "").replace("/watch?v=", "")
                        break
                
                if not live_video_id and related:
                    live_video_id = related[0].get("url", "").replace("/watch?v=", "")

                if live_video_id:
                    # 2. Ambil Stream HLS (m3u8)
                    stream_res = requests.get(f"{instance}/streams/{live_video_id}", headers=HEADERS, timeout=5)
                    if stream_res.status_code == 200:
                        stream_data = stream_res.json()
                        hls_url = stream_data.get("hls")
                        if hls_url:
                            return hls_url
        except Exception:
            continue
    return None

def get_hls_via_invidious(target):
    """Fallback ke Invidious API."""
    for instance in INVIDIOUS_INSTANCES:
        try:
            url = f"{instance}/api/v1/channels/{target}"
            res = requests.get(url, headers=HEADERS, timeout=5)
            if res.status_code == 200:
                data = res.json()
                videos = data.get("latestVideos", [])
                video_id = None
                for v in videos:
                    if v.get("isLive"):
                        video_id = v.get("videoId")
                        break
                if not video_id and videos:
                    video_id = videos[0].get("videoId")
                
                if video_id:
                    v_res = requests.get(f"{instance}/api/v1/videos/{video_id}", headers=HEADERS, timeout=5)
                    if v_res.status_code == 200:
                        v_data = v_res.json()
                        if v_data.get("hlsUrl"):
                            return v_data.get("hlsUrl")
        except Exception:
            continue
    return None

def get_hls_via_ytdlp(target):
    """Fallback akhir menggunakan yt-dlp android player client."""
    url = target
    if target.startswith("UC") or target.startswith("@"):
        url = f"https://www.youtube.com/{target if target.startswith('@') else 'channel/' + target}/live"

    cmd = [
        "yt-dlp",
        "-g",
        "-f", "b/bestpass/best",
        "--extractor-args", "youtube:player_client=android,ios",
        "--no-warnings",
        url
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        out = res.stdout.strip()
        if out and ("m3u8" in out or "googlevideo.com" in out):
            return out.splitlines()[0]
    except Exception:
        pass
    return None

def process_target(target):
    if ".m3u8" in target and "youtube.com" not in target:
        return target

    # Tier 1: Piped API
    url = get_hls_via_piped(target)
    if url:
        return url

    # Tier 2: Invidious API
    url = get_hls_via_invidious(target)
    if url:
        return url

    # Tier 3: Direct yt-dlp
    url = get_hls_via_ytdlp(target)
    if url:
        return url

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
