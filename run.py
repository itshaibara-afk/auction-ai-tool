"""起動用エントリーポイント。

1人で使う場合:
    python run.py
    → ブラウザで http://127.0.0.1:5050

社内で共有する場合（同じネットワーク内の他のPCからアクセス可能にする）:
    python run.py --share
    → 起動時に表示されるURL（http://<このPCのIPアドレス>:5050）を社内メンバーに共有
    → 事前に「設定」画面で共有合言葉を設定しておくこと
"""
import os
import socket
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app import app  # noqa: E402


def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:  # noqa: BLE001
        return "127.0.0.1"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    share = "--share" in sys.argv or os.environ.get("SHARE") == "1"
    host = "0.0.0.0" if share else "127.0.0.1"
    if share:
        print("=" * 60)
        print("  社内共有モードで起動します")
        print(f"  同じネットワークの人はこのURLでアクセスできます:")
        print(f"    http://{local_ip()}:{port}")
        print("  ※「設定」画面で共有合言葉を設定してから共有してください")
        print("=" * 60)
    app.run(host=host, port=port, debug=False)
