"""
Popon license proxy.

Masalah: URL /exec dari Google Apps Script selalu melakukan redirect (302) ke
script.googleusercontent.com/macros/echo sebelum isi JSON sebenarnya dikirim.
Browser biasa mengikuti redirect itu tanpa masalah, tapi fetch() bawaan
GrowLauncher (dan beberapa HTTP client sederhana lain) tidak menanganinya
dengan benar, jadi hasilnya kosong atau error.

Proxy ini jalan di server biasa (bukan di game), memanggil Apps Script
dengan library `requests` (yang mengikuti redirect dengan sempurna, persis
seperti browser), lalu mengembalikan hasil JSON-nya langsung -- tanpa
redirect -- ke pemanggil. Skrip Lua tinggal memanggil URL proxy ini,
bukan URL Apps Script secara langsung.

Env vars:
  APPS_SCRIPT_URL  -- URL /exec dari Code.gs (wajib)
  PORT             -- opsional, disediakan otomatis oleh Render/Fly/dll.
"""
import os

import requests
from flask import Flask, request, jsonify

APPS_SCRIPT_URL = os.environ["APPS_SCRIPT_URL"]
TIMEOUT_SECONDS = 15

app = Flask(__name__)


@app.get("/license")
def license_check():
    # Teruskan apa adanya semua query string yang dikirim skrip Lua
    # (action, code, growid, session). doGet() di Code.gs sudah membatasi
    # sendiri hanya action=check yang diproses, jadi proxy ini aman untuk
    # diteruskan tanpa validasi tambahan di sisi sini.
    params = dict(request.args)

    try:
        resp = requests.get(
            APPS_SCRIPT_URL,
            params=params,
            timeout=TIMEOUT_SECONDS,
            allow_redirects=True,  # ini kunci perbaikannya
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException:
        return jsonify({"ok": False, "reason": "server"}), 200
    except ValueError:
        # Apps Script merespons tapi bukan JSON (jarang terjadi, mis. halaman error Google)
        return jsonify({"ok": False, "reason": "server"}), 200

    return jsonify(data), 200


@app.get("/healthz")
def healthz():
    return {"ok": True}, 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
