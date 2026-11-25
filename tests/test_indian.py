#!/usr/bin/env python3
"""Checks for Indian languages in scripts/transcribe.py: Latin-letter spelling for every Indian script, the Hinglish
word fixes, and the Sarvam timing logic (no network, no Whisper). Standard library only: python3 tests/test_indian.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from transcribe import INDIAN, map_onto_timing, romanize, split_pieces, to_devanagari, typed  # noqa: E402

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


# Each language in its own script → how people type it in Latin letters.
ROMAN = [
    ("hi", "भाई ये जगह एकदम मस्त है।", "bhai yeh jagah ekdum mast hai."),
    ("hi", "नहीं बहुत ज़्यादा अच्छा", "nahi bahut zyada accha"),
    ("mr", "काय सीन आहे", "kaay seen aahe"),
    ("pa", "ਕੀ ਸੀਨ ਆ ਪੱਕਾ", "ki seen aa pakka"),
    ("gu", "સીન છે મજા", "seen chhe maja"),
    ("bn", "কি দারুণ জায়গা রে", "ki darun jayga re"),
    ("bn", "কেমন", "kemon"),
    ("or", "କି ସିନ୍ ଭଲ", "ki sin bhala"),
    ("ta", "என்ன சீன் டா மச்சி", "enna seen da machi"),
    ("ta", "சரி தம்பி சிங்கம் வாழைப்பழம்", "sari thambi singam vaazhaippazham"),
    ("te", "సీన్ రా బావ", "seen ra baava"),
    ("kn", "ಸೀನ್ ಗುರು", "seen guru"),
    ("ml", "എന്ത് സീൻ അവൻ അത്", "enthu seen avan athu"),
]

TYPED = [("nahin", "nahi"), ("Bohot,", "Bahut,"), ("kyaa?", "kya?"), ("India", "India"), ("hello", "hello")]


def main():
    check(len(INDIAN) == 11, f"expected 11 Indian languages, got {len(INDIAN)}")
    check(INDIAN["or"][1] is None, "Odia should be marked as unknown to Whisper")
    for lang, src, want in ROMAN:
        got = romanize(src, lang)
        check(got == want, f"{lang}: {src!r} → {got!r}, expected {want!r}")
    for src, want in TYPED:
        check(typed(src) == want, f"typed({src!r}) → {typed(src)!r}, expected {want!r}")
    # English and numbers pass through untouched, even inside a Hinglish line.
    check(romanize("India aur $5,000", "hi") == "India aur $5,000", "Latin text and numbers must pass through")
    # Every Indian script maps onto Devanagari.
    check(to_devanagari("க") == "क" and to_devanagari("క") == "क" and to_devanagari("ক") == "क", "script offset mapping")

    # Sarvam timing: n words over m Whisper words keeps the span and the order, and never runs backwards.
    timing = [{"text": f"w{i}", "startMs": i * 400, "endMs": i * 400 + 300} for i in range(6)]
    same = map_onto_timing(["a", "b", "c", "d", "e", "f"], timing)
    check([w["startMs"] for w in same] == [w["startMs"] for w in timing], "equal counts keep Whisper's times")
    fewer = map_onto_timing(["India", "aur", "Bangladesh"], timing)
    check(fewer[0]["startMs"] == 0 and fewer[-1]["endMs"] <= timing[-1]["endMs"], "fewer words stay inside the piece")
    check(all(a["startMs"] <= b["startMs"] for a, b in zip(fewer, fewer[1:])), "mapped words stay in order")
    more = map_onto_timing([f"x{i}" for i in range(9)], timing)
    check(len(more) == 9 and all(w["endMs"] > w["startMs"] for w in more), "more words each get a real duration")
    check(map_onto_timing([], timing) == [] and map_onto_timing(["a"], []) == [], "empty input gives no words")

    # Pieces stay under the limit and cover every word once.
    long = [{"text": "w", "startMs": i * 1000, "endMs": i * 1000 + 800} for i in range(70)]
    pieces = split_pieces(long, 25.0)
    check(sum(len(p) for p in pieces) == 70, "every word lands in exactly one piece")
    check(all(p[-1]["endMs"] - p[0]["startMs"] <= 25000 for p in pieces), "no piece is over 25 s")

    if failures:
        print("FAILED")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print(f"ok: {len(ROMAN)} Latin-letter cases in 10 scripts, {len(TYPED)} Hinglish fixes, Sarvam timing and pieces passed")


if __name__ == "__main__":
    main()
