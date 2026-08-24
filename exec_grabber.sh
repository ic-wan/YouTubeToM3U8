#!/bin/bash

# Install/update yt-dlp ke versi terbaru
python3 -m pip install -U yt-dlp requests

# Jalankan skrip grabber
python3 YouTubeLinkGrabber.py > playlist.m3u
