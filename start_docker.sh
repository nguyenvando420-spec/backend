#!/usr/bin/env bash
set -e

# Tự động phát hiện IP máy tính (hoạt động trên macOS & Linux)
DETECTED_IP=$(python3 -c "
import socket
try:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(0.5)
        s.connect(('8.8.8.8', 80))
        print(s.getsockname()[0])
except Exception:
    print('')
" 2>/dev/null || ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")

DETECTED_HOSTNAME=$(hostname 2>/dev/null || echo "host-machine")

if [ -n "$DETECTED_IP" ]; then
  export HOST_IP="$DETECTED_IP"
fi

if [ -n "$DETECTED_HOSTNAME" ]; then
  export HOST_NAME="$DETECTED_HOSTNAME"
fi

echo "========================================================"
echo "🚀 Khởi động Backend bằng Docker Compose"
echo "📍 IP Máy tính (Host IP):   ${HOST_IP:-127.0.0.1}"
echo "📍 Tên máy tính (Hostname):  ${HOST_NAME:-localhost}"
echo "========================================================"

docker compose up -d "$@"
