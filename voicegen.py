import asyncio
import json
import os
import re
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional, Callable
from xml.sax.saxutils import escape as xml_escape

HAS_EDGE = False
HAS_OPENAI = False
HAS_QWEN = False
HAS_PYDUB = False
HAS_SOUNDFILE = False
HAS_LIBROSA = False

try:
    import edge_tts
    HAS_EDGE = True
except ImportError:
    pass

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    pass

try:
    from qwen_tts import Qwen3TTSModel
    HAS_QWEN = True
except ImportError:
    pass

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    pass

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    pass

try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    pass


class Engine(Enum):
    EDGE = "edge"
    OPENAI = "openai"
    QWEN3 = "qwen3"
    GTTS = "gtts"


class Emotion(Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    EXCITED = "excited"
    WHISPER = "whisper"
    CALM = "calm"
    TENSE = "tense"
    NARRATION = "narration"


EMOTION_SSML = {
    Emotion.HAPPY: '<prosody rate="110%" pitch="+8%"><emphasis level="moderate">',
    Emotion.SAD: '<prosody rate="85%" pitch="-10%" volume="-15%">',
    Emotion.ANGRY: '<prosody rate="115%" pitch="+5%" volume="+20%">',
    Emotion.EXCITED: '<prosody rate="120%" pitch="+12%" volume="+10%"><emphasis level="strong">',
    Emotion.WHISPER: '<prosody volume="-40%" pitch="+2%" rate="90%">',
    Emotion.CALM: '<prosody rate="90%" pitch="-3%" volume="-5%">',
    Emotion.TENSE: '<prosody rate="105%" pitch="+3%" volume="+5%">',
    Emotion.NARRATION: '<prosody rate="95%" pitch="-2%" volume="+3%">',
    Emotion.NEUTRAL: '',
}

EMOTION_OPENAI = {
    Emotion.NEUTRAL: 'alloy',
    Emotion.HAPPY: 'nova',
    Emotion.SAD: 'shimmer',
    Emotion.ANGRY: 'onyx',
    Emotion.EXCITED: 'fable',
    Emotion.WHISPER: 'shimmer',
    Emotion.CALM: 'alloy',
    Emotion.TENSE: 'onyx',
    Emotion.NARRATION: 'echo',
}


@dataclass
class VoiceProfile:
    name: str
    engine: str = "edge"
    voice: str = "en-US-AriaNeural"
    pitch: str = "0%"
    rate: str = "0%"
    volume: str = "0%"
    emotion: str = "neutral"
    language: str = "en"
    style: str = ""
    role: str = ""
    openai_model: str = "tts-1-hd"
    openai_voice: str = "alloy"


@dataclass
class AudioClip:
    path: Path
    start: float = 0.0
    end: float = 0.0
    text: str = ""
    speaker: str = ""
    emotion: str = "neutral"
    duration: float = 0.0


@dataclass
class Segment:
    text: str
    speaker: str = ""
    emotion: str = "neutral"
    start: float = 0.0
    end: float = 0.0


_voice_bank: dict[str, VoiceProfile] = {}
_default_profiles: dict[str, VoiceProfile] = {}

DEFAULT_VOICES = {
    "male": "en-US-GuyNeural",
    "female": "en-US-AriaNeural",
    "child": "en-US-AnaNeural",
    "narrator": "en-US-DavisNeural",
}


def normalize_lang(lang: str) -> str:
    return lang.split("-")[0].split("_")[0].lower()


def build_ssml(text: str, voice: str, pitch: str = "0%", rate: str = "0%",
               volume: str = "0%", emotion: Emotion = Emotion.NEUTRAL,
               lang: str = "en-US") -> str:
    safe = xml_escape(text)
    inner = EMOTION_SSML.get(emotion, '')
    close = ''
    if inner:
        close = '</emphasis></prosody>' if emotion in (Emotion.HAPPY, Emotion.EXCITED) else '</prosody>'
    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"'
        f' xml:lang="{lang}">'
        f'<voice name="{voice}">'
        f'<prosody pitch="{pitch}" rate="{rate}" volume="{volume}">'
        f'{inner}{safe}{close}'
        f'</prosody></voice></speak>'
    )


def get_edge_voices(sync: bool = False) -> list[dict]:
    if not HAS_EDGE:
        return []
    try:
        if sync:
            voices = asyncio.run(edge_tts.list_voices())
        else:
            try:
                loop = asyncio.get_running_loop()
                voices = asyncio.run_coroutine_threadsafe(
                    edge_tts.list_voices(), loop).result()
            except RuntimeError:
                voices = asyncio.run(edge_tts.list_voices())
        return sorted(voices, key=lambda v: v.get("ShortName", ""))
    except Exception:
        return []


def list_voices(lang: str = "", engine: str = "edge", gender: str = ""
                ) -> list[str]:
    if engine == "edge":
        voices = get_edge_voices()
        result = []
        for v in voices:
            short = v.get("ShortName", "")
            locale = v.get("Locale", "")
            g = v.get("Gender", "")
            if lang and not locale.startswith(lang.split("-")[0]):
                continue
            if gender and gender.lower() not in g.lower():
                continue
            result.append(short)
        return result
    elif engine == "openai":
        return ["alloy", "echo", "fable", "nova", "onyx", "shimmer"]
    elif engine == "qwen3":
        return ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric",
                "Ryan", "Aiden", "Ono_Anna", "Sohee"]
    return []


def voice_supports_emotion(engine: str) -> bool:
    return engine in ("edge", "openai")


def register_voice(name: str, profile: VoiceProfile):
    _voice_bank[name] = profile


def get_voice(name: str) -> Optional[VoiceProfile]:
    return _voice_bank.get(name)


def save_voice_bank(path: str):
    data = {k: asdict(v) for k, v in _voice_bank.items()}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_voice_bank(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for k, v in data.items():
        _voice_bank[k] = VoiceProfile(**v)


def set_default_role(gender: str = "male", engine: str = "edge",
                     voice: str = "") -> VoiceProfile:
    if not voice:
        voice = DEFAULT_VOICES.get(gender, "en-US-AriaNeural")
    profile = VoiceProfile(
        name=f"default_{gender}",
        engine=engine,
        voice=voice,
    )
    _default_profiles[gender] = profile
    return profile


def get_default_role(gender: str = "male") -> VoiceProfile:
    return _default_profiles.get(gender) or set_default_role(gender)


class VoiceGenerator:
    def __init__(self, bank_dir: str = "", engine: str = "auto",
                 openai_api_key: str = "", openai_base_url: str = "",
                 qwen3_model_path: str = "", device: str = "cpu"):
        self.bank_dir = Path(bank_dir) if bank_dir else Path.cwd() / "voices"
        self.bank_dir.mkdir(parents=True, exist_ok=True)
        self._engine_override = engine
        self._openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY", "")
        self._openai_base_url = openai_base_url or os.getenv("OPENAI_BASE_URL", "")
        self._qwen3_model = None
        self._qwen3_path = qwen3_model_path
        self._device = device
        self._openai_client = None
        self._stats = {"generated": 0, "failed": 0, "total_chars": 0}
        self._on_progress: Optional[Callable] = None
        bank_file = self.bank_dir / "voice_bank.json"
        if bank_file.exists():
            try:
                load_voice_bank(str(bank_file))
            except Exception:
                pass

    def on_progress(self, cb: Callable):
        self._on_progress = cb

    def _report(self, msg: str, data: dict = None):
        if self._on_progress:
            self._on_progress(msg, data or {})
        else:
            print(f"  {msg}")

    def _resolve_engine(self, engine: str = "") -> str:
        e = engine or self._engine_override or "auto"
        if e == "auto":
            if HAS_EDGE:
                return "edge"
            if HAS_OPENAI and self._openai_api_key:
                return "openai"
            return "gtts"
        return e

    def _get_openai(self):
        if self._openai_client is None:
            kwargs = {"api_key": self._openai_api_key}
            if self._openai_base_url:
                kwargs["base_url"] = self._openai_base_url
            self._openai_client = openai.OpenAI(**kwargs)
        return self._openai_client

    def _ensure_qwen3(self):
        if self._qwen3_model is not None:
            return True
        if not HAS_QWEN:
            return False
        if not self._qwen3_path:
            self._qwen3_path = str(self.bank_dir.parent / "models" / "Qwen3-TTS-12Hz-0.6B-CustomVoice")
        path = Path(self._qwen3_path)
        if not (path / "config.json").exists():
            return False
        try:
            import torch
            dtype = torch.bfloat16 if self._device == "cuda" else torch.float32
            self._qwen3_model = Qwen3TTSModel.from_pretrained(
                str(path), device_map=self._device, dtype=dtype
            )
            return True
        except Exception:
            return False

    def _save_bank(self):
        bank_file = self.bank_dir / "voice_bank.json"
        save_voice_bank(str(bank_file))

    def register(self, name: str, engine: str = "edge",
                 voice: str = "", gender: str = "male",
                 pitch: str = "0%", rate: str = "0%",
                 emotion: str = "neutral", language: str = "en",
                 style: str = "") -> VoiceProfile:
        if not voice:
            voice = DEFAULT_VOICES.get(gender, "en-US-AriaNeural")
        profile = VoiceProfile(
            name=name, engine=engine, voice=voice,
            pitch=pitch, rate=rate, emotion=emotion,
            language=normalize_lang(language), style=style,
        )
        register_voice(name, profile)
        self._save_bank()
        return profile

    def list_registered(self) -> list[tuple[str, VoiceProfile]]:
        return list(_voice_bank.items())

    def remove(self, name: str):
        if name in _voice_bank:
            del _voice_bank[name]
            self._save_bank()

    def stats(self) -> dict:
        s = dict(self._stats)
        s["voices_in_bank"] = len(_voice_bank)
        s["engines_available"] = {
            "edge": HAS_EDGE,
            "openai": HAS_OPENAI,
            "qwen3": HAS_QWEN,
            "pydub": HAS_PYDUB,
        }
        return s

    def synthesize(self, text: str, voice_profile: VoiceProfile = None,
                   engine: str = "", voice: str = "",
                   emotion: str = "", out_path: str = "",
                   pitch: str = "0%", rate: str = "0%",
                   lang: str = "") -> Optional[Path]:
        e = self._resolve_engine(engine)
        if voice_profile:
            e = voice_profile.engine
            voice = voice_profile.voice
            emotion = emotion or voice_profile.emotion
            pitch = pitch or voice_profile.pitch
            rate = rate or voice_profile.rate
            lang = lang or voice_profile.language
        if not voice:
            voice = "en-US-AriaNeural"
        if not emotion:
            emotion = "neutral"
        em = Emotion(emotion) if isinstance(emotion, str) else emotion
        if not lang:
            lang = "en"

        if not out_path:
            out_path = str(self.bank_dir / f"gen_{uuid.uuid4().hex[:8]}.wav")
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        if e == "edge":
            ok = self._synth_edge(text, voice, str(out), pitch, rate, em, lang)
        elif e == "openai":
            ok = self._synth_openai(text, voice, str(out), em, lang)
        elif e == "qwen3":
            ok = self._synth_qwen3(text, voice, str(out), em, lang)
        else:
            ok = self._synth_gtts(text, str(out), lang)

        if ok:
            self._stats["generated"] += 1
            self._stats["total_chars"] += len(text)
            return out
        self._stats["failed"] += 1
        return None

    def _synth_edge(self, text: str, voice: str, out: str,
                    pitch: str, rate: str, emotion: Emotion, lang: str) -> bool:
        if not HAS_EDGE:
            return False
        try:
            ssml = build_ssml(text, voice, pitch, rate, "0%", emotion, lang)
            async def go():
                c = edge_tts.Communicate(ssml, voice)
                await c.save(out)
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, go())
                future.result(timeout=120)
            return Path(out).exists() and Path(out).stat().st_size > 500
        except Exception:
            return False

    def _synth_openai(self, text: str, voice: str, out: str,
                      emotion: Emotion, lang: str) -> bool:
        if not HAS_OPENAI or not self._openai_api_key:
            return False
        try:
            client = self._get_openai()
            ov = EMOTION_OPENAI.get(emotion, voice)
            response = client.audio.speech.create(
                model="tts-1-hd",
                voice=ov,
                input=text,
            )
            response.stream_to_file(out)
            p = Path(out)
            return p.exists() and p.stat().st_size > 500
        except Exception:
            return False

    def _synth_qwen3(self, text: str, voice: str, out: str,
                     emotion: Emotion, lang: str) -> bool:
        if not self._ensure_qwen3():
            return False
        try:
            import soundfile as sf
            wavs, sr = self._qwen3_model.generate_custom_voice(
                text=[text], speaker=[voice],
                language=["English"], max_new_tokens=2048,
            )
            sf.write(out, wavs[0], sr)
            p = Path(out)
            return p.exists() and p.stat().st_size > 500
        except Exception:
            return False

    def _synth_gtts(self, text: str, out: str, lang: str) -> bool:
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(out)
            p = Path(out)
            return p.exists() and p.stat().st_size > 500
        except Exception:
            return False

    def batch(self, segments: list[Segment],
              engine: str = "", voice_profile: VoiceProfile = None,
              voice: str = "", emotion: str = "",
              pitch: str = "", rate: str = "",
              out_dir: str = "", max_workers: int = 4
              ) -> list[AudioClip]:
        out_dir = out_dir or str(self.bank_dir / "batch")
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        results: list[Optional[AudioClip]] = [None] * len(segments)

        def gen_one(i: int, seg: Segment) -> AudioClip:
            spk = seg.speaker or voice
            em = seg.emotion or emotion or "neutral"
            vp = _voice_bank.get(seg.speaker) if seg.speaker else voice_profile
            out = str(Path(out_dir) / f"seg_{i:04d}.wav")
            path = self.synthesize(
                text=seg.text,
                voice_profile=vp,
                voice=spk,
                emotion=em,
                pitch=pitch,
                rate=rate,
                lang=normalize_lang(vp.language if vp else ""),
                out_path=out,
                engine=engine,
            )
            dur = 0.0
            if path and HAS_LIBROSA:
                try:
                    dur = float(librosa.get_duration(filename=str(path)))
                except Exception:
                    pass
            return AudioClip(
                path=path or Path(""),
                start=seg.start,
                end=seg.end or (seg.start + dur),
                text=seg.text,
                speaker=spk,
                emotion=em,
                duration=dur,
            )

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(gen_one, i, seg): i
                       for i, seg in enumerate(segments)}
            done = 0
            total = len(segments)
            for f in as_completed(futures):
                i = futures[f]
                try:
                    results[i] = f.result()
                except Exception as e:
                    self._report(f"[!] Segment {i} failed: {e}")
                    results[i] = AudioClip(path=Path(""), text=segments[i].text,
                                           speaker=segments[i].speaker)
                done += 1
                if done % max(1, total // 10) == 0 or done == total:
                    self._report(f"Progress: {done}/{total}")
        return [r for r in results if r and r.path and r.path.exists()]

    def apply_fx(self, input_path: str, output_path: str = "",
                 speed: float = 1.0, pitch_shift: float = 0.0,
                 volume_db: float = 0.0, reverb: float = 0.0,
                 normalize: bool = True, trim_silence: bool = True,
                 highpass: float = 0.0, lowpass: float = 0.0
                 ) -> Optional[Path]:
        if not HAS_PYDUB:
            return Path(input_path) if Path(input_path).exists() else None
        out = Path(output_path) if output_path else Path(input_path)
        try:
            audio = AudioSegment.from_file(input_path)
            if trim_silence:
                audio = audio.strip_silence(threshold=-40, padding=50)
            if speed != 1.0:
                frame_rate = int(audio.frame_rate * speed)
                audio = audio._spawn(audio.raw_data, overrides={
                    "frame_rate": frame_rate})
                audio = audio.set_frame_rate(44100)
            if pitch_shift != 0.0:
                if HAS_LIBROSA:
                    y, sr = librosa.load(input_path, sr=None)
                    y_shifted = librosa.effects.pitch_shift(
                        y=y, sr=sr, n_steps=pitch_shift)
                    import soundfile as sf
                    tmp = str(out) + ".pitch_tmp.wav"
                    sf.write(tmp, y_shifted, sr)
                    audio = AudioSegment.from_file(tmp)
                    Path(tmp).unlink(missing_ok=True)
                else:
                    octaves = pitch_shift / 12.0
                    audio = audio._spawn(audio.raw_data, overrides={
                        "frame_rate": int(audio.frame_rate * (2 ** octaves))})
                    audio = audio.set_frame_rate(44100)
            if volume_db != 0.0:
                audio = audio + volume_db
            if reverb > 0:
                decay = 1.0 - min(reverb, 0.9)
                segment = audio
                for i in range(1, int(reverb * 10)):
                    echo = segment - (i * 2)
                    delay = int(50 * i)
                    silent = AudioSegment.silent(delay, frame_rate=audio.frame_rate)
                    audio = audio.overlay(echo, position=delay)
            if highpass > 0:
                (Path(out.parent) / "_tmp").mkdir(parents=True, exist_ok=True)
                tmp_raw = str(Path(out.parent) / "_tmp" / "raw.wav")
                audio.export(tmp_raw, format="wav")
                tmp_filtered = str(Path(out.parent) / "_tmp" / "filtered.wav")
                os.system(
                    f'ffprobe -i "{tmp_raw}" 2>/dev/null; '
                    f'ffmpeg -i "{tmp_raw}" -af "highpass=f={highpass}" '
                    f'"{tmp_filtered}" -y 2>/dev/null'
                )
                if Path(tmp_filtered).exists():
                    audio = AudioSegment.from_file(tmp_filtered)
                Path(tmp_raw).unlink(missing_ok=True)
            if lowpass > 0:
                (Path(out.parent) / "_tmp").mkdir(parents=True, exist_ok=True)
                tmp_raw = str(Path(out.parent) / "_tmp" / "raw.wav")
                audio.export(tmp_raw, format="wav")
                tmp_filtered = str(Path(out.parent) / "_tmp" / "filtered.wav")
                os.system(
                    f'ffmpeg -i "{tmp_raw}" -af "lowpass=f={lowpass}" '
                    f'"{tmp_filtered}" -y 2>/dev/null'
                )
                if Path(tmp_filtered).exists():
                    audio = AudioSegment.from_file(tmp_filtered)
                Path(tmp_raw).unlink(missing_ok=True)
            if normalize:
                peak = audio.max_possible_amplitude
                max_amp = audio.max
                if max_amp > 0:
                    gain = min(peak / max_amp, 4.0)
                    audio = audio.apply_gain(20 * (gain ** 0.5 - 1))
            audio.export(str(out), format="wav")
            return out if out.exists() else None
        except Exception:
            return None

    def concatenate(self, clips: list[AudioClip], output_path: str,
                    crossfade_ms: int = 0, normalize: bool = True
                    ) -> Optional[Path]:
        if not HAS_PYDUB or not clips:
            return None
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            combined = AudioSegment.empty()
            for clip in clips:
                if not clip.path.exists():
                    continue
                seg = AudioSegment.from_file(str(clip.path))
                if normalize:
                    peak = seg.max_possible_amplitude
                    max_amp = seg.max
                    if max_amp > 0:
                        gain = min(peak / max_amp, 4.0)
                        seg = seg.apply_gain(20 * (gain ** 0.5 - 1))
                if crossfade_ms > 0 and len(combined) > 0:
                    combined = combined.append(seg, crossfade=crossfade_ms)
                else:
                    combined = combined + seg
            combined.export(str(out), format="wav", parameters=["-ac", "1"])
            return out if out.exists() else None
        except Exception:
            return None

    def mix_with_timing(self, clips: list[AudioClip], output_path: str,
                        bgm_path: str = "", bgm_volume: float = 0.15,
                        total_duration: float = 0.0
                        ) -> Optional[Path]:
        if not HAS_PYDUB or not clips:
            return None
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            if bgm_path and Path(bgm_path).exists():
                bgm = AudioSegment.from_file(bgm_path)
                if total_duration > 0:
                    bgm = bgm[:int(total_duration * 1000)]
                bgm = bgm - abs(20 * (1 - bgm_volume))
            else:
                max_end = max((c.end for c in clips if c.end > 0),
                              default=0) or max(
                    (c.start + c.duration for c in clips), default=10)
                total_dur = max(max_end, total_duration)
                bgm = AudioSegment.silent(int(total_dur * 1000) + 5000)
            mixed = bgm
            for clip in clips:
                if not clip.path.exists():
                    continue
                seg = AudioSegment.from_file(str(clip.path))
                pos = int(clip.start * 1000)
                mixed = mixed.overlay(seg, position=pos)
            mixed.export(str(out), format="wav")
            return out if out.exists() else None
        except Exception:
            return None

    def clone_to_profile(self, reference_audio: str, voice_name: str,
                         engine: str = "edge") -> VoiceProfile:
        profile = VoiceProfile(
            name=voice_name,
            engine=engine,
            voice=DEFAULT_VOICES.get("male", "en-US-AriaNeural"),
        )
        register_voice(voice_name, profile)
        self._save_bank()
        return profile


class VoiceCLI:
    def __init__(self, generator: VoiceGenerator = None):
        self.gen = generator or VoiceGenerator()

    def run(self, args: list[str] = None):
        import argparse
        parser = argparse.ArgumentParser(
            description="voicegen — Realistic Human Voice Generator")
        sub = parser.add_subparsers(dest="command")

        p_say = sub.add_parser("say", help="Generate speech from text")
        p_say.add_argument("text", nargs="+")
        p_say.add_argument("--voice", "-v", default="en-US-AriaNeural")
        p_say.add_argument("--engine", "-e", default="edge",
                           choices=["edge", "openai", "qwen3", "gtts"])
        p_say.add_argument("--emotion", "-m", default="neutral",
                           choices=[e.value for e in Emotion])
        p_say.add_argument("--pitch", default="0%")
        p_say.add_argument("--rate", default="0%")
        p_say.add_argument("--out", "-o", default="", help="Output WAV path")
        p_say.add_argument("--play", "-p", action="store_true",
                           help="Play audio after generation")

        p_list = sub.add_parser("list", help="List available voices")
        p_list.add_argument("--lang", default="", help="Filter by language")
        p_list.add_argument("--engine", "-e", default="edge",
                            choices=["edge", "openai", "qwen3"])
        p_list.add_argument("--gender", "-g", default="",
                            choices=["male", "female", ""])

        p_register = sub.add_parser("register", help="Register a voice profile")
        p_register.add_argument("name")
        p_register.add_argument("--voice", "-v", default="")
        p_register.add_argument("--engine", "-e", default="edge")
        p_register.add_argument("--gender", "-g", default="male")
        p_register.add_argument("--pitch", default="0%")
        p_register.add_argument("--rate", default="0%")
        p_register.add_argument("--emotion", default="neutral")

        p_bank = sub.add_parser("bank", help="List registered profiles")
        p_batch = sub.add_parser("batch", help="Batch process segments")
        p_batch.add_argument("--input", "-i", required=True,
                             help="JSON file with segments")
        p_batch.add_argument("--out-dir", "-o", default="")
        p_batch.add_argument("--workers", "-w", type=int, default=4)
        p_batch.add_argument("--voice", "-v", default="")
        p_batch.add_argument("--engine", "-e", default="auto")
        p_batch.add_argument("--emotion", default="neutral")

        p_fx = sub.add_parser("fx", help="Apply audio effects to a WAV")
        p_fx.add_argument("input")
        p_fx.add_argument("--speed", type=float, default=1.0)
        p_fx.add_argument("--pitch", type=float, default=0.0)
        p_fx.add_argument("--volume", type=float, default=0.0)
        p_fx.add_argument("--reverb", type=float, default=0.0)
        p_fx.add_argument("--out", "-o", default="")
        p_fx.add_argument("--normalize", action="store_true")

        p_info = sub.add_parser("info", help="Show engine stats")

        p_concat = sub.add_parser("concat", help="Concatenate audio clips")
        p_concat.add_argument("--input", "-i", required=True,
                              help="JSON array of clip paths")
        p_concat.add_argument("--out", "-o", required=True)
        p_concat.add_argument("--crossfade", type=int, default=50)

        parsed = parser.parse_args(args)

        if parsed.command == "say":
            text = " ".join(parsed.text)
            path = self.gen.synthesize(
                text=text, voice=parsed.voice,
                engine=parsed.engine,
                emotion=parsed.emotion,
                pitch=parsed.pitch, rate=parsed.rate,
            )
            if path:
                print(f"[OK] {path}")
                if parsed.play and HAS_SOUNDFILE:
                    import sounddevice as sd
                    data, sr = sf.read(str(path))
                    sd.play(data, sr)
                    sd.wait()
            else:
                print("[!] Synthesis failed")

        elif parsed.command == "list":
            voices = list_voices(
                lang=parsed.lang, engine=parsed.engine,
                gender=parsed.gender)
            print(f"Voices ({len(voices)}):")
            for v in voices:
                print(f"  {v}")

        elif parsed.command == "register":
            self.gen.register(
                name=parsed.name, engine=parsed.engine,
                voice=parsed.voice, gender=parsed.gender,
                pitch=parsed.pitch, rate=parsed.rate,
                emotion=parsed.emotion)
            print(f"[OK] Registered '{parsed.name}'")

        elif parsed.command == "bank":
            profiles = self.gen.list_registered()
            if not profiles:
                print("No profiles registered.")
                return
            print(f"{'Name':<20} {'Engine':<8} {'Voice':<30} {'Emotion':<12} "
                  f"{'Pitch':<8} {'Rate':<8}")
            print("-" * 90)
            for name, p in profiles:
                print(f"{name:<20} {p.engine:<8} {p.voice:<30} "
                      f"{p.emotion:<12} {p.pitch:<8} {p.rate:<8}")

        elif parsed.command == "batch":
            with open(parsed.input, "r", encoding="utf-8") as f:
                data = json.load(f)
            segments = []
            for s in data:
                segments.append(Segment(
                    text=s.get("text", ""),
                    speaker=s.get("speaker", ""),
                    emotion=s.get("emotion", parsed.emotion),
                    start=s.get("start", 0.0),
                    end=s.get("end", 0.0),
                ))
            clips = self.gen.batch(
                segments, engine=parsed.engine,
                voice=parsed.voice, max_workers=parsed.workers,
                out_dir=parsed.out_dir)
            report = []
            for c in clips:
                report.append({
                    "path": str(c.path), "speaker": c.speaker,
                    "start": c.start, "end": c.end,
                    "duration": c.duration, "text": c.text[:80],
                })
            manifest = Path(parsed.out_dir or "output") / "manifest.json"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            with open(manifest, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            print(f"[OK] {len(clips)} clips → {manifest}")

        elif parsed.command == "fx":
            out = parsed.out or parsed.input
            path = self.gen.apply_fx(
                parsed.input, output_path=out,
                speed=parsed.speed, pitch_shift=parsed.pitch,
                volume_db=parsed.volume, reverb=parsed.reverb,
                normalize=parsed.normalize)
            if path:
                print(f"[OK] {path}")
            else:
                print("[!] FX processing failed")

        elif parsed.command == "concat":
            with open(parsed.input, "r", encoding="utf-8") as f:
                data = json.load(f)
            clips = []
            for item in data:
                clips.append(AudioClip(
                    path=Path(item.get("path", "")),
                    text=item.get("text", ""),
                    speaker=item.get("speaker", ""),
                ))
            path = self.gen.concatenate(
                clips, parsed.out, crossfade_ms=parsed.crossfade)
            if path:
                print(f"[OK] {path}")
            else:
                print("[!] Concatenation failed")

        elif parsed.command == "info":
            s = self.gen.stats()
            print(f"Generated: {s['generated']} files")
            print(f"Failed: {s['failed']}")
            print(f"Total chars: {s['total_chars']}")
            print(f"Voice bank entries: {s['voices_in_bank']}")
            print(f"Engines:")
            for eng, avail in s['engines_available'].items():
                print(f"  {eng}: {'✓' if avail else '✗'}")
        else:
            parser.print_help()


def generate(text: str, voice: str = "en-US-AriaNeural",
             engine: str = "edge", emotion: str = "neutral",
             pitch: str = "0%", rate: str = "0%",
             out_path: str = "", play: bool = False) -> Optional[Path]:
    gen = VoiceGenerator()
    path = gen.synthesize(
        text=text, voice=voice, engine=engine,
        emotion=emotion, pitch=pitch, rate=rate,
        out_path=out_path,
    )
    if path and play and HAS_SOUNDFILE:
        import sounddevice as sd
        data, sr = sf.read(str(path))
        sd.play(data, sr)
        sd.wait()
    return path


if __name__ == "__main__":
    VoiceCLI().run()
