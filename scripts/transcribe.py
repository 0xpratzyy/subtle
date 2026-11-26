#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["faster-whisper>=1.1", "mlx-whisper>=0.4; sys_platform == 'darwin' and platform_machine == 'arm64'"]
# ///
"""Transcribe a video locally with faster-whisper or mlx-whisper on Apple Silicon.

    uv run scripts/transcribe.py video.mp4 --out words.json [--lang en] [--vocab "Refs, Claude"] [--script roman]

Without uv: `pip install faster-whisper`, then run it with python.
The result is cached by the file's SHA-256, so a second run on the same video returns at once.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_MODEL = "mlx-community/whisper-large-v3-turbo"
FASTER_MODEL = "large-v3-turbo"
MLX_MODELS = {name: f"mlx-community/whisper-{name}" for name in ("tiny", "base", "small", "medium", "large-v3")}
MLX_MODELS["large-v3-turbo"] = DEFAULT_MODEL
CACHE_VERSION = 5  # bump when transcription or spelling logic changes, so old cache entries are not reused


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def probe(path):
    """Display width/height (rotation applied), fps and duration via ffprobe."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,r_frame_rate,avg_frame_rate:stream_disposition=attached_pic:stream_side_data=rotation:stream_tags=rotate:format=duration",
         "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    streams = [x for x in d.get("streams", []) if not (x.get("disposition") or {}).get("attached_pic")]
    if not streams:  # a song or a voice memo: no picture. The runner makes a canvas and sets the real size.
        return {"width": 1080, "height": 1920, "fps": 30.0, "durationMs": int(float(d["format"]["duration"]) * 1000), "audioOnly": True}
    s = streams[0]
    w, h = int(s["width"]), int(s["height"])
    rot = 0
    for sd in s.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(float(sd["rotation"]))
    if not rot and s.get("tags", {}).get("rotate"):
        rot = int(s["tags"]["rotate"])
    if abs(rot) % 180 == 90:
        w, h = h, w
    num, den = (s.get("avg_frame_rate") or s["r_frame_rate"]).split("/")
    fps = float(num) / float(den) if float(den) else 30.0
    if not fps or fps > 240:
        num, den = s["r_frame_rate"].split("/")
        fps = float(num) / float(den)
    return {"width": w, "height": h, "fps": round(fps, 3), "durationMs": int(float(d["format"]["duration"]) * 1000)}


# ---- Indian languages ----
# code: name, Whisper's code (None: Whisper cannot hear it), Sarvam's code, the vowel a bare consonant carries, whether
# a word-final one is silent (Hindi "ghar", Tamil "naama"), whether a long vowel inside a word is typed double (baat).
INDIAN = {
    "hi": ("Hindi", "hi", "hi-IN", "a", True, True),
    "mr": ("Marathi", "mr", "mr-IN", "a", True, True),
    "pa": ("Punjabi", "pa", "pa-IN", "a", True, True),
    "gu": ("Gujarati", "gu", "gu-IN", "a", True, True),
    "bn": ("Bengali", "bn", "bn-IN", "o", True, False),
    "or": ("Odia", None, "od-IN", "a", False, False),
    "ta": ("Tamil", "ta", "ta-IN", "a", False, True),
    "te": ("Telugu", "te", "te-IN", "a", False, True),
    "kn": ("Kannada", "kn", "kn-IN", "a", False, True),
    "ml": ("Malayalam", "ml", "ml-IN", "a", False, True),
    "ur": ("Urdu", "ur", "ur-IN", "a", True, True),
}

# The Indian scripts share one Unicode layout, so each letter maps to the Devanagari letter at the same offset and the
# Devanagari rules below write all of them in Latin letters.
_SCRIPT_BLOCKS = [(0x0980, "bn"), (0x0A00, "pa"), (0x0A80, "gu"), (0x0B00, "or"), (0x0B80, "ta"), (0x0C00, "te"), (0x0C80, "kn"), (0x0D00, "ml")]
# Malayalam letters that end a syllable; the joiner marks them so the final-u rule (enthu) leaves them alone.
_CHILLU = {"ൺ": "ण्\u200d", "ൻ": "न्\u200d", "ർ": "र्\u200d", "ൽ": "ल्\u200d", "ൾ": "ळ्\u200d", "ൿ": "क्\u200d"}
_EXTRA = {"ৎ": "त्", "ஃ": "", "ௗ": "", "ൗ": "ौ", "ൎ": ""}


def to_devanagari(text):
    """Any Indian script → Devanagari, letter by letter (Gurmukhi addak doubles the next consonant, tippi is an n)."""
    text = re.sub("\u0A71(.)", lambda m: m.group(1) + "\u0A4D" + m.group(1), text).replace("\u0A70", "\u0A02")
    out = []
    for ch in text:
        if ch in _CHILLU:
            out.append(_CHILLU[ch])
            continue
        if ch in _EXTRA:
            out.append(_EXTRA[ch])
            continue
        cp = ord(ch)
        for base, _ in _SCRIPT_BLOCKS:
            if base <= cp < base + 0x80:
                ch = chr(cp - base + 0x0900)
                break
        out.append(ch)
    import unicodedata
    return unicodedata.normalize("NFD", "".join(out))  # precomposed nukta letters (ड़, य़) become letter + nukta


# ---- Devanagari → Roman (casual "Hinglish" spelling, best effort) ----
_CONS = {"क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng", "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n",
         "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
         "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh",
         "ष": "sh", "स": "s", "ह": "h", "ळ": "l", "ऴ": "zh", "ऱ": "r", "ऩ": "n", "क़": "q", "ख़": "kh", "ग़": "g", "ज़": "z", "ड़": "r", "ढ़": "rh", "फ़": "f"}
_VOW = {"अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ऋ": "ri", "ऑ": "o", "ऎ": "e", "ऒ": "o"}
_MATRA = {"ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u", "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ृ": "ri", "ॉ": "o", "ॆ": "e", "ॊ": "o"}
_NUKTA, _VIRAMA = "़", "्"
# How people actually type the most common Hindi words; the rules below cannot guess these.
_COMMON = {"में": "mein", "मैं": "main", "हैं": "hain", "है": "hai", "नहीं": "nahi", "हम": "hum", "और": "aur", "यह": "yeh", "ये": "yeh",
           "वह": "woh", "वो": "woh", "क्या": "kya", "क्यों": "kyun", "सिर्फ": "sirf", "लेकिन": "lekin", "दोस्तों": "doston",
           "आप": "aap", "आपको": "aapko", "कि": "ki", "की": "ki", "का": "ka", "के": "ke", "को": "ko", "से": "se", "पर": "par",
           "हुआ": "hua", "हुई": "hui", "था": "tha", "थी": "thi", "थे": "the", "भी": "bhi", "ही": "hi", "तो": "toh", "अब": "ab",
           "बहुत": "bahut", "अच्छा": "accha", "कौन": "kaun", "कुछ": "kuch", "मुझे": "mujhe", "इंडिया": "India", "इंडिय": "India",
           "यार": "yaar", "भाई": "bhai", "अभी": "abhi", "कभी": "kabhi", "सब": "sab", "सबसे": "sabse", "बात": "baat",
           "करना": "karna", "करते": "karte", "करेंगे": "karenge", "किया": "kiya", "रहा": "raha", "रहे": "rahe", "रही": "rahi",
           "गया": "gaya", "गए": "gaye", "गई": "gayi", "चलो": "chalo", "देखो": "dekho", "मतलब": "matlab", "ठीक": "theek",
           "पता": "pata", "लोग": "log", "लोगों": "logon", "वाला": "wala", "वाले": "wale", "वाली": "wali", "अपना": "apna",
           "अपने": "apne", "हमें": "humein", "तुम": "tum", "तुम्हें": "tumhe", "जब": "jab", "तब": "tab", "यहां": "yahan",
           "यहाँ": "yahan", "वहां": "wahan", "वहाँ": "wahan", "क्योंकि": "kyunki", "इसलिए": "isliye", "सच": "sach",
           "एकदम": "ekdum", "मस्त": "mast", "ज़्यादा": "zyada", "ज्यादा": "zyada", "थोड़ा": "thoda", "सही": "sahi",
           "दिन": "din", "साल": "saal", "पैसे": "paise", "काम": "kaam", "घर": "ghar", "दोस्त": "dost", "हां": "haan",
           "हाँ": "haan", "मैंने": "maine", "हमने": "humne", "आज": "aaj", "कल": "kal", "फिर": "phir", "शायद": "shayad",
           "बिल्कुल": "bilkul", "जगह": "jagah", "सकते": "sakte", "सकता": "sakta", "चाहिए": "chahiye", "होगा": "hoga",
           "होता": "hota", "होती": "hoti", "वाह": "waah", "प्यार": "pyaar", "ज़िंदगी": "zindagi", "जिंदगी": "zindagi"}
# Whisper's own Latin spellings of Hindi words that people type differently.
_TYPED = {"nahin": "nahi", "nahee": "nahi", "kyaa": "kya", "kyon": "kyun", "kyoon": "kyun", "bahot": "bahut", "bohot": "bahut",
          "bhot": "bahut", "achha": "accha", "achcha": "accha", "thik": "theek", "yaha": "yahan", "vaha": "wahan", "vahan": "wahan",
          "mai": "main", "mujhey": "mujhe", "hamein": "humein", "ham": "hum", "aapko": "aapko", "jyada": "zyada", "zyaada": "zyada",
          "ekdam": "ekdum", "lekhin": "lekin", "matlb": "matlab", "doston": "doston", "dosto": "doston"}
_LATIN_FIX = str.maketrans({"š": "sh", "č": "ch", "ñ": "n", "ā": "aa", "ī": "ee", "ū": "oo", "ṭ": "t", "ḍ": "d", "ṇ": "n", "ś": "sh", "ṣ": "sh"})


def romanize_word(word, vowel="a", drop_final=True, double_long=True, common=True):
    """Transliterate one Devanagari word. Drops the silent final and medial 'a' the way people type Hinglish.

    For other languages: `vowel` is the vowel a bare consonant carries (Bengali "o"), `drop_final` whether it is
    silent at the end of a word (not in Tamil, Telugu, Kannada, Malayalam, Odia), `double_long` whether a long vowel
    inside a word is typed double, `common` whether to use the Hindi word list.
    """
    if common and word in _COMMON:
        return _COMMON[word]
    units = []  # (roman, has_inherent_a, is_consonant)
    i, n = 0, len(word)
    while i < n:
        ch = word[i]
        two = word[i:i + 2]
        if two in _CONS or ch in _CONS:
            base = _CONS[two] if two in _CONS else _CONS[ch]
            i += 2 if two in _CONS else 1
            if i < n and word[i] == _NUKTA:
                base = {"j": "z", "ph": "f", "k": "q", "d": "r", "dh": "rh", "l": "zh"}.get(base, base)
                i += 1
            if i < n and word[i] == _VIRAMA:
                units.append([base, False, True]); i += 1
            elif i < n and word[i] in _MATRA:
                m = word[i]
                rom = _MATRA[m]
                # a long vowel in the middle of a word is typed double (baat, teen, door); at the end it is single (sona, ki)
                if double_long and i + 1 < n and m in "ाीू" and word[i + 1] not in "ंँ":
                    rom = {"ा": "aa", "ी": "ee", "ू": "oo"}[m]
                units.append([base + rom, False, True]); i += 1
            else:
                units.append([base, True, True])
        elif ch in _VOW:
            units.append([_VOW[ch], False, False]); i += 1
        elif ch in "ंँ":
            units.append(["n", False, False]); i += 1
        elif ch == "ः":
            units.append(["h", False, False]); i += 1
        else:
            units.append([ch, False, False]); i += 1
    out = []
    for k, (rom, inherent, cons) in enumerate(units):
        if inherent:
            last = k == len(units) - 1
            nxt = units[k + 1] if not last else None
            # final 'a' is silent; so is a medial 'a' before a consonant that carries its own vowel (kar-na, not karana)
            medial_drop = drop_final and (k >= 1 and nxt is not None and nxt[2] and not nxt[1] and nxt[0][-1:] in "aeiou")
            if last and len(units) > 1 and drop_final:
                pass
            elif medial_drop:
                pass
            else:
                rom += vowel
        out.append(rom)
    return "".join(out)


# How each language's letters are typed where it differs from Hindi, applied to the Devanagari form (before) and the
# Latin result (after). Tamil: ச is "s" (sari) but ச்ச is "ch" (machi), ட is "d" (da), த is "th" (thambi).
# Malayalam: ത is "th" (athu) and a word-final ് is said "u" (enthu).
_BEFORE = {"ta": [("च्च", "छ"), ("च", "स"), ("ट", "ड"), ("त", "थ"), ("म्प", "म्ब"), ("ङ्क", "ङ्ग")], "ml": [("त", "थ")]}
_AFTER = {"ta": [("chh", "ch"), ("dd", "tt"), ("thth", "tth"), ("ngg", "ng")], "ml": [("chch", "ch"), ("thth", "tth")]}


def typed(word):
    """Whisper's Latin spelling of a common Hindi word → how people type it, keeping case and trailing punctuation."""
    m = re.match(r"^([A-Za-z]+)(\W*)$", word)
    if not m or m.group(1).lower() not in _TYPED:
        return word
    w = _TYPED[m.group(1).lower()]
    if m.group(1)[0].isupper():
        w = w[0].upper() + w[1:]
    return w + m.group(2)


def romanize(text, lang="hi"):
    """Indian-script runs → Latin letters, then strip the stray accents Whisper sometimes adds to romanised Hindi."""
    import unicodedata
    _, _, _, vowel, drop_final, double_long = INDIAN.get(lang, INDIAN["hi"])
    hindi = lang in ("hi", "ur")
    text = to_devanagari(text.replace("।", ".").replace("॥", "."))
    for a, b in _BEFORE.get(lang, []):
        text = text.replace(a, b)
    if lang == "ml":
        text = re.sub("(?<=[क-ह])\u094D(?![ऀ-ॿ\u200d])", "\u0941", text)
    text = text.replace("\u200d", "")
    text = re.sub(r"[ऀ-ॿ]+", lambda m: romanize_word(m.group(0), vowel, drop_final, double_long, common=hindi), text).translate(_LATIN_FIX)
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    for a, b in _AFTER.get(lang, []):
        text = text.replace(a, b)
    return typed(text) if hindi else text


ROMAN_HINT = ("Yeh video Hinglish mein hai. Hindi ko Roman script mein likho aur English words ko English mein rakho: "
              "doston, aaj hum baat karenge, yeh sirf ek example nahi hai, kya aapko pata hai.")


# ---- Optional: Sarvam for Indian languages (--engine sarvam, your own SARVAM_API_KEY) ----
# Sarvam's speech-to-text knows Indian languages and code-mixed speech much better than Whisper, but it times phrases,
# not words, and takes at most 30 s per request. So Whisper still listens first: its words decide where to cut the audio
# and when each word lands, and Sarvam supplies the text for each piece.
SARVAM_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_MODEL = "saaras:v4"
MAX_PIECE_S = 25.0
PAD_S = 0.15


def split_pieces(words, max_s=MAX_PIECE_S):
    """Groups Whisper's words into pieces under `max_s` seconds, cut at the widest pause in each piece's last third."""
    pieces, i = [], 0
    while i < len(words):
        start = words[i]["startMs"] / 1000
        j = i
        while j + 1 < len(words) and words[j + 1]["endMs"] / 1000 - start <= max_s:
            j += 1
        if j + 1 < len(words):
            best, best_gap = j, -1.0
            for k in range(max(i, int(i + (j - i) * 0.66)), j + 1):
                gap = words[k + 1]["startMs"] - words[k]["endMs"] if k + 1 < len(words) else float("inf")
                if gap > best_gap:
                    best, best_gap = k, gap
            j = best
        pieces.append(words[i:j + 1])
        i = j + 1
    return pieces


def map_onto_timing(texts, timing):
    """Places n Sarvam words over the m Whisper words of the same piece: each gets a slice of Whisper's index space,
    weighted by length, and its times are read off Whisper's words, so pauses between words survive."""
    n, m = len(texts), len(timing)
    if not n or not m:
        return []
    if n == m:
        return [{**timing[i], "text": t} for i, t in enumerate(texts)]

    def at(x, edge):
        k = min(m - 1, int(x))
        frac = x - k
        w = timing[k]
        if edge == "start" and frac == 0:
            return w["startMs"]
        if edge == "end" and x >= m:
            return timing[-1]["endMs"]
        return w["startMs"] + (w["endMs"] - w["startMs"]) * min(1.0, frac)

    weights = [max(1, len(t)) for t in texts]
    total, acc, out = sum(weights), 0, []
    for i, t in enumerate(texts):
        a = acc / total * m
        acc += weights[i]
        b = acc / total * m
        start, end = at(a, "start"), at(b, "end")
        k = min(m - 1, int(a))
        if k + 1 < m and end > timing[k]["endMs"] and timing[k + 1]["startMs"] - timing[k]["endMs"] > 200:
            end = timing[k]["endMs"]  # never stretch a word across a pause
        out.append({"text": t, "startMs": int(round(start)), "endMs": int(round(max(start + 50, end))), "prob": 1.0})
    return out


def _wav_slice(path, start_s, end_s):
    import io
    import wave
    with wave.open(str(path), "rb") as src:
        rate = src.getframerate()
        src.setpos(max(0, int(start_s * rate)))
        frames = src.readframes(max(1, int((end_s - max(0, start_s)) * rate)))
        buf = io.BytesIO()
        with wave.open(buf, "wb") as dst:
            dst.setnchannels(src.getnchannels())
            dst.setsampwidth(src.getsampwidth())
            dst.setframerate(rate)
            dst.writeframes(frames)
    return buf.getvalue()


def sarvam_text(wav_bytes, key, lang_code, script):
    """One piece of audio → Sarvam's transcript. English letters: `translit`; the language's own script: `codemix`."""
    import urllib.error
    import urllib.request
    import uuid
    boundary = uuid.uuid4().hex
    fields = {"model": SARVAM_MODEL, "mode": "translit" if script == "roman" else "codemix", "language_code": lang_code}
    body = b"".join(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items())
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="piece.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode()
             + wav_bytes + f"\r\n--{boundary}--\r\n".encode())
    req = urllib.request.Request(SARVAM_URL, data=body, method="POST",
                                 headers={"api-subscription-key": key, "Content-Type": f"multipart/form-data; boundary={boundary}"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode()).get("transcript") or ""
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < 3:
                time.sleep(0.8 * 2 ** attempt)
                continue
            raise SystemExit(f"transcribe.py: Sarvam returned {e.code}: {e.read().decode(errors='replace')[:300]}")
    return ""


def sarvam_words(wav, whisper_words, key, lang_code, script):
    """Whisper's timing, Sarvam's words. A piece Sarvam returns nothing for keeps Whisper's words."""
    from concurrent.futures import ThreadPoolExecutor
    pieces = split_pieces(whisper_words)

    def run(piece):
        s0, s1 = piece[0]["startMs"] / 1000 - PAD_S, piece[-1]["endMs"] / 1000 + PAD_S
        tokens = sarvam_text(_wav_slice(wav, s0, s1), key, lang_code, script).split()
        return map_onto_timing(tokens, piece) if tokens else piece

    with ThreadPoolExecutor(max_workers=4) as pool:
        return [w for chunk in pool.map(run, pieces) for w in chunk]


def pick_backend(requested):
    """Use mlx on Apple Silicon when installed; faster-whisper is the portable default."""
    if requested != "auto":
        return requested
    import platform
    if sys.platform == "darwin" and platform.machine() == "arm64":
        try:
            import mlx_whisper  # noqa: F401
            return "mlx"
        except ImportError:
            pass
    return "faster"


def run_mlx(wav, a, hints):
    try:
        import mlx_whisper
    except ImportError:
        sys.exit("transcribe.py: mlx-whisper is not installed. Use --backend faster, or `pip install mlx-whisper`.")
    kwargs = dict(path_or_hf_repo=a.model, word_timestamps=True, condition_on_previous_text=False, verbose=None)
    if a.whisper_lang:
        kwargs["language"] = a.whisper_lang
    if hints:
        kwargs["initial_prompt"] = " ".join(hints)
    result = mlx_whisper.transcribe(str(wav), **kwargs)
    segments = [[{"word": w.get("word") or "", "start": float(w["start"]), "end": float(w["end"]),
                  "probability": float(w.get("probability", 0))} for w in (seg.get("words") or [])]
                for seg in result.get("segments", [])]
    return segments, result.get("language") or a.whisper_lang


def run_faster(wav, a, hints):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("transcribe.py: faster-whisper is not installed. Run with `uv run`, or `pip install faster-whisper`.")
    device = a.device
    if device == "auto":
        try:
            import ctranslate2
            device = "cuda" if ctranslate2.get_cuda_device_count() else "cpu"
        except Exception:
            device = "cpu"
    compute = a.compute_type
    if compute == "auto":
        compute = "float16" if device == "cuda" else "int8"
    model = WhisperModel(a.model, device=device, compute_type=compute)
    kwargs = dict(word_timestamps=True, condition_on_previous_text=False, vad_filter=a.vad, beam_size=5)
    if a.whisper_lang:
        kwargs["language"] = a.whisper_lang
    if hints:
        kwargs["initial_prompt"] = " ".join(hints)
    segments, info = model.transcribe(str(wav), **kwargs)
    normalized = [[{"word": w.word or "", "start": float(w.start), "end": float(w.end),
                    "probability": float(w.probability)} for w in (seg.words or [])] for seg in segments]
    return normalized, info.language or a.whisper_lang


def main():
    ap = argparse.ArgumentParser(description="Word-level transcription with faster-whisper or mlx-whisper.")
    ap.add_argument("video")
    ap.add_argument("--out", help="where to write words.json (default: the cache folder)")
    ap.add_argument("--lang", help="language code, e.g. en, es, or an Indian one: " + ", ".join(INDIAN) + " (default: detect)")
    ap.add_argument("--vocab", default="", help="names and brand words, comma-separated; passed to Whisper as a hint")
    ap.add_argument("--script", choices=["native", "roman"], default="native",
                    help="roman: write an Indian language in Latin letters, the way people type it (Hinglish, Tanglish...)")
    ap.add_argument("--engine", choices=["whisper", "sarvam"], default="whisper",
                    help="sarvam: Sarvam AI writes the words for an Indian language (needs SARVAM_API_KEY; Whisper still times them)")
    ap.add_argument("--hinglish", action="store_true", help="short for --lang hi --script roman")
    ap.add_argument("--model", default=os.environ.get("SUBTLE_MODEL"), help="model name (default large-v3-turbo; use small on a slow CPU)")
    ap.add_argument("--backend", choices=["auto", "faster", "mlx"], default="auto")
    ap.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    ap.add_argument("--compute-type", choices=["auto", "int8", "int8_float16", "float16", "float32"], default="auto")
    ap.add_argument("--vad", action="store_true", help="skip silence (speech only; not for singing)")
    ap.add_argument("--cache-dir", default=os.environ.get("SUBTLE_CACHE", str(Path.home() / ".cache" / "subtle")))
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args()

    if a.hinglish:
        a.lang, a.script = a.lang or "hi", "roman"
    a.backend = pick_backend(a.backend)
    a.model = a.model or (DEFAULT_MODEL if a.backend == "mlx" else FASTER_MODEL)
    if a.backend == "mlx" and a.model in MLX_MODELS:
        a.model = MLX_MODELS[a.model]
    indian = INDIAN.get(a.lang or "")
    sarvam_key = os.environ.get("SARVAM_API_KEY", "").strip()
    if a.engine == "sarvam":
        if not indian:
            sys.exit(f"transcribe.py: --engine sarvam needs an Indian --lang ({', '.join(INDIAN)})")
        if not sarvam_key:
            sys.exit("transcribe.py: --engine sarvam needs SARVAM_API_KEY (your own key from dashboard.sarvam.ai)")
    if indian and indian[1] is None and a.engine != "sarvam":
        sys.exit(f"transcribe.py: Whisper does not know {indian[0]}; use --engine sarvam with SARVAM_API_KEY")
    video = Path(a.video).expanduser().resolve()
    if not video.exists():
        sys.exit(f"transcribe.py: no such file: {video}")
    hinglish_path = a.script == "roman" and (a.lang or "") in ("hi", "ur")
    a.whisper_lang = "hi" if hinglish_path else (indian[1] if indian else a.lang)
    t0 = time.time()
    digest = sha256(video)
    key = hashlib.sha256(json.dumps([CACHE_VERSION, a.backend, a.lang, a.vocab, a.script, a.model, a.engine,
                                    a.vad, a.device, a.compute_type]).encode()).hexdigest()[:10]
    cdir = Path(a.cache_dir) / digest[:16]
    cdir.mkdir(parents=True, exist_ok=True)
    cached = cdir / f"words.{key}.json"
    out_path = Path(a.out).expanduser() if a.out else cached

    if cached.exists() and not a.no_cache:
        data = json.loads(cached.read_text(encoding="utf-8"))
        if out_path != cached:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({"out": str(out_path), "words": len(data["words"]), "language": data["language"], "cached": True, "seconds": round(time.time() - t0, 2)}))
        return

    meta = probe(video)
    wav = cdir / "audio.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn", "-ar", "16000", "-ac", "1", str(wav)], check=True)

    hints = []
    if hinglish_path and a.engine == "whisper":
        hints.append(ROMAN_HINT)  # with this hint Whisper writes most Hindi in Latin letters by itself
    if a.vocab.strip():
        hints.append("Vocabulary: " + a.vocab.strip().rstrip(".") + ".")
    segments, detected = (run_mlx if a.backend == "mlx" else run_faster)(wav, a, hints)
    result = {"language": detected}

    words = []
    for seg in segments:
        seg_words = 0
        for w in seg:
            raw = w["word"]
            text = raw.strip()
            if not text:
                continue
            if a.script == "roman" and a.engine == "whisper":
                text = romanize(text, a.lang or "hi")
            if words and not raw.startswith(" ") and seg_words > 0 and re.match(r"^[\w,.'’%-]", text):
                # Whisper split one word into two tokens ("25" + ",000"): glue it back together
                words[-1]["text"] += text
                words[-1]["endMs"] = int(round(w["end"] * 1000))
                continue
            seg_words += 1
            words.append({"text": text, "startMs": int(round(w["start"] * 1000)), "endMs": int(round(w["end"] * 1000)),
                          "prob": round(w["probability"], 3)})
    if a.engine == "sarvam" and words:
        words = sarvam_words(wav, words, sarvam_key, indian[2], a.script)
    data = {"version": 1, "source": {"sha256": digest, **meta}, "language": a.lang or result.get("language"), "model": a.model,
            "engine": a.engine, "backend": a.backend, "script": a.script, "words": words}
    cached.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    if out_path != cached:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    secs = time.time() - t0
    print(json.dumps({"out": str(out_path), "words": len(words), "language": data["language"], "cached": False,
                      "seconds": round(secs, 2), "secondsPerMinuteOfVideo": round(secs / max(1e-6, meta["durationMs"] / 60000), 2)}))


if __name__ == "__main__":
    main()
