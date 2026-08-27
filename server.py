#!/usr/bin/env python3
"""Flask server: serves static files + /api/tts endpoint using voicegen.py"""

import os, sys, tempfile, uuid, io, json
from pathlib import Path

from flask import Flask, send_file, send_from_directory, request, jsonify

sys.path.insert(0, str(Path(__file__).parent))
from voicegen import VoiceGenerator

HERE = Path(__file__).parent

# Voice profiles for Quranic words
PROFILES = {
    "ar": {"engine": "edge", "voice": "ar-SA-HamedNeural", "lang": "ar-SA"},
    "en": {"engine": "edge", "voice": "en-US-AriaNeural", "lang": "en-US"},
}

gen = VoiceGenerator(bank_dir=str(HERE / ".voice_cache"))

app = Flask(__name__, static_folder=str(HERE))


@app.route("/")
def index():
    return send_from_directory(HERE, "index.html")


@app.route("/api/tts", methods=["POST"])
def tts():
    data = request.get_json(force=True) or {}
    text = data.get("text", "").strip()
    lang = data.get("lang", "ar")
    voice = data.get("voice", "")

    if not text:
        return jsonify({"error": "No text provided"}), 400

    profile = PROFILES.get(lang, PROFILES["ar"])
    engine = profile["engine"]
    if not voice:
        voice = profile["voice"]
    lang_code = profile["lang"]

    # Generate audio to temp file
    tmp = str(HERE / ".voice_cache" / f"tts_{uuid.uuid4().hex[:12]}.wav")
    Path(tmp).parent.mkdir(parents=True, exist_ok=True)

    out = gen.synthesize(
        text=text,
        engine=engine,
        voice=voice,
        lang=lang_code,
        out_path=tmp,
    )

    if out and out.exists():
        return send_file(str(out), mimetype="audio/wav")
    else:
        return jsonify({"error": "TTS synthesis failed"}), 500


@app.route("/api/voices", methods=["GET"])
def list_voices():
    from voicegen import list_voices as lv
    ar = lv(lang="ar", engine="edge")
    en = lv(lang="en", engine="edge")
    return jsonify({"arabic": ar, "english": en})


@app.route("/api/stats", methods=["GET"])
def stats():
    return jsonify(gen.stats())


# Serve audio directory
AUDIO_DIR = HERE / "audio"

@app.route("/audio/<path:filename>")
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)

# Serve static files (JS, CSS, assets)
@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(HERE, filename)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Quranic Words TTS server")
    parser.add_argument("--port", type=int, default=8888, help="Port to listen on (default: 8888)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    args = parser.parse_args()
    print(f"Quranic Words App — TTS server at http://localhost:{args.port}")
    print("  Arabic voice: ar-SA-HamedNeural (male, Saudi)")
    print("  Press Ctrl+C to stop")
    app.run(host=args.host, port=args.port, debug=False)
