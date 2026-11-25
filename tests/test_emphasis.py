#!/usr/bin/env python3
"""Checks for number tokens (scripts/spoken_numbers.py) and highlight picks (scripts/emphasis.py).
Standard library only: python3 tests/test_emphasis.py"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from emphasis import rule_picks, split_words  # noqa: E402
from spoken_numbers import group_digits, normalise_numbers  # noqa: E402

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


def words(line, step=300):
    return [{"text": t, "startMs": k * step, "endMs": k * step + step - 20} for k, t in enumerate(line.split())]


def norm(line, lang=None, grouping="auto"):
    return " | ".join(w["text"] for w in normalise_numbers(words(line), lang, grouping))


NUMBERS = [
    ("gold price is five thousand dollars now", "gold | price | is | $5,000 | now"),
    # money keeps its cents; a percentage or an amount in millions does not need them
    ("it costs 3.50 dollars", "it | costs | $3.50"),
    ("it costs $3.50 today", "it | costs | $3.50 | today"),
    ("about 2.9 euros", "about | €2.90"),
    ("growth of 3.5 percent", "growth | of | 3.5%"),
    ("a $3.5 million round", "a | $3.5 million | round"),
    ("gold price is $5000.", "gold | price | is | $5,000."),
    ("it costs 5000 dollars, okay", "it | costs | $5,000, | okay"),
    ("up 40 percent since 1991.", "up | 40% | since | 1991."),
    ("forty percent of people", "40% | of | people"),
    ("three point five percent growth", "3.5% | growth"),
    ("gold has crossed one lakh rupees for 10 grams.", "gold | has | crossed | ₹1 lakh | for | 10 | grams."),
    ("Rs 500 only", "₹500 | only"),
    ("Rs. 5 lakh salary", "₹5 lakh | salary"),
    ("it is 5 crore rupees", "it | is | ₹5 crore"),
    ("a hundred tons at a time", "100 | tons | at | a | time"),
    ("twenty five thousand people", "25,000 | people"),
    ("five hundred and twenty dollars", "$520"),
    ("in nineteen ninety one, India", "in | 1991, | India"),
    ("in twenty twenty four we", "in | 2024 | we"),
    ("$5 million round", "$5 million | round"),
    ("five million dollars raised", "$5 million | raised"),
    ("1500000 users", "1,500,000 | users"),
    ("two thousand and five hundred", "2,500"),
    ("at 2.5 percent", "at | 2.5%"),
    # left alone on purpose
    ("three times, and every single time", "three | times, | and | every | single | time"),
    ("one of the best", "one | of | the | best"),
    ("ten, twenty, thirty", "ten, | twenty, | thirty"),
    ("one two three go", "one | two | three | go"),
    ("3x faster and 10k users", "3x | faster | and | 10k | users"),
    ("millions of families", "millions | of | families"),
    ("a million reasons", "a | million | reasons"),
    ("ten twenty in the morning", "ten | twenty | in | the | morning"),
    ("the world's 10 biggest", "the | world's | 10 | biggest"),
]


SPANISH_NUMBERS = [
    ("el oro cuesta cinco mil dólares ahora", "el | oro | cuesta | $5,000 | ahora"),
    ("cuesta 3,50 euros", "cuesta | €3,50"),
    ("cuesta 5000 dolares, vale", "cuesta | $5,000, | vale"),
    ("subió un 40 por ciento desde 1991.", "subió | un | 40% | desde | 1991."),
    ("cuarenta por ciento de la gente", "40% | de | la | gente"),
    ("tres coma cinco por ciento de crecimiento", "3.5% | de | crecimiento"),
    ("cien por ciento seguro", "100% | seguro"),
    ("veinticinco mil personas", "25,000 | personas"),
    ("dieciséis mil quinientas personas", "16,500 | personas"),
    ("ciento treinta y cinco personas", "135 | personas"),
    ("treinta y cinco euros", "€35"),
    ("5 mil dólares", "$5,000"),
    ("en mil novecientos noventa y uno, México", "en | 1991, | México"),
    ("en dos mil veinticuatro nosotros", "en | 2024 | nosotros"),
    ("dos mil personas", "2,000 | personas"),
    ("cinco millones de dólares recaudados", "$5 millones | recaudados"),
    ("un millón de dólares", "$1 millón"),
    ("cinco mil millones de euros", "€5,000 millones"),
    # the transcript already writes 5.000 and 3,5: read them right and keep that convention
    ("cuesta 5.000 euros al mes", "cuesta | €5.000 | al | mes"),
    ("subió 3,5% este año", "subió | 3,5% | este | año"),
    ("vale 1.234,56 euros", "vale | €1.234,56"),
    ("3,5 millones de euros", "€3,5 millones"),
    # left alone on purpose
    ("tres veces, y cada vez", "tres | veces, | y | cada | vez"),
    ("uno de los mejores", "uno | de | los | mejores"),
    ("diez, veinte, treinta", "diez, | veinte, | treinta"),
    ("un día cualquiera", "un | día | cualquiera"),
    ("un millón de razones", "un | millón | de | razones"),
    ("mil gracias por venir", "mil | gracias | por | venir"),
    ("tengo treinta y tú veinte", "tengo | treinta | y | tú | veinte"),
]


def main():
    for line, want in NUMBERS:
        got = norm(line)
        check(got == want, f"numbers: {line!r} -> {got!r}, expected {want!r}")
    for line, want in SPANISH_NUMBERS:
        got = norm(line, "es")
        check(got == want, f"numbers: Spanish {line!r} -> {got!r}, expected {want!r}")
    check(norm("cinco mil dólares y 3.5 por ciento", "es", "european") == "$5.000 | y | 3,5%", "numbers: --numbers european")
    check(norm("cuesta 5.000 euros", "es", "western") == "cuesta | €5,000", "numbers: Spanish '5.000' with --numbers western")
    check(norm("once people came at 5.000 volts") == "once | people | came | at | 5 | volts", "numbers: Spanish rules must not run on English")
    check(norm("paanch lakh rupaye lagte hain", "hi") == "₹5 lakh | lagte | hain", "numbers: Hindi 'paanch lakh rupaye'")
    check(norm("do baar bola", "hi") == "do | baar | bola", "numbers: Hindi 'do' without a unit must stay a word")
    check(norm("1500000 rupees") == "₹15,00,000", "numbers: rupee amounts use Indian grouping by default")
    check(norm("1500000 rupees", None, "western") == "₹1,500,000", "numbers: --numbers western")
    check(group_digits(12345678, True) == "1,23,45,678", "numbers: Indian digit grouping")
    merged = normalise_numbers(words("price is five thousand dollars now"))
    tok = next(w for w in merged if w["text"] == "$5,000")
    check(tok["startMs"] == 600 and tok["endMs"] == 1480, "numbers: a merged token must span all the words it replaced")

    check(split_words("gold, $5,000") == ["gold", "$5,000"], "split_words: 'gold, $5,000'")
    check(split_words("gold,three,won") == ["gold", "three", "won"], "split_words: 'gold,three,won'")
    check(split_words("25,000,1968") == ["25,000", "1968"], "split_words: '25,000,1968'")

    # rule picks: the number wins the page; names and contrast words follow; filler words never
    def picks(line, mode="auto", forced=(), size=4, lang=None):
        ws = normalise_numbers(words(line), lang)
        pages = [{"startMs": ws[i]["startMs"], "endMs": ws[min(i + size, len(ws)) - 1]["endMs"],
                  "words": [dict(w, emphasis=False) for w in ws[i:i + size]]} for i in range(0, len(ws), size)]
        rule_picks(pages, mode, forced, lang)
        return [(w["text"], w["reason"]) for p in pages for w in p["words"] if w["emphasis"]], pages

    # Spanish: its own contrast and stop words; a capital after ¿ or ¡ starts a sentence, it is not a name
    got, _ = picks("¿Sabes cuánto cuesta? Cuesta cinco mil dólares y nunca baja ni sube. ¡Nadie lo esperaba! Entonces María se mudó "
                   "a Guatemala con su familia.", size=3, lang="es")
    texts = [t for t, _ in got]
    check(("$5,000", "price") in got, f"rules: Spanish '$5,000' must be highlighted, got {got}")
    check(("nunca", "contrast word") in got and ("¡Nadie", "contrast word") in got, f"rules: Spanish contrast words, got {got}")
    check(("María", "name") in got and ("Guatemala", "name") in got, f"rules: Spanish names, got {got}")
    check(not any(t in ("¿Sabes", "Cuesta", "Entonces", "con", "su", "lo") for t in texts), f"rules: Spanish sentence starts or filler words picked: {got}")
    got, _ = picks("y luego ¿Sabes qué pasó con todo eso", size=4, lang="es")
    check(not any(r == "name" for _, r in got), f"rules: a capital after ¿ is not a name, got {got}")
    got, _ = picks("my son has no sin and once had a con", size=3)
    check(not any(r == "count" for _, r in got), f"rules: Spanish lists must not run on English, got {got}")

    got, _ = picks("so the gold price is five thousand dollars today okay")
    check(("$5,000", "price") in got, f"rules: '$5,000' must be highlighted, got {got}")
    got, _ = picks("it went up 40 percent that year in 1991 when Meera moved to Mumbai and never came back", size=2)
    texts = [t for t, _ in got]
    check("40%" in texts and "1991" in texts, f"rules: percentage and year, got {got}")
    check("Meera" in texts and "Mumbai" in texts and "never" in texts, f"rules: names and the contrast word, got {got}")
    check(not any(t.lower() in ("it", "in", "to", "and", "the", "when") for t in texts), f"rules: filler words picked: {got}")
    got, pages = picks("it went up 40 percent that year in 1991 when Meera moved to Mumbai", mode="numbers", size=2)
    check([t for t, _ in got] == ["40%", "1991"], f"rules: --emphasis numbers picked {got}")
    got, _ = picks("it went up 40 percent in 1991 when Meera moved to Mumbai", mode="off")
    check(got == [], f"rules: --emphasis off picked {got}")
    got, _ = picks("it went up 40 percent in 1991 when Meera moved to Mumbai", mode="off", forced=["mumbai"])
    check([t for t, _ in got] == ["Mumbai"], f"rules: forced word, got {got}")
    got, pages = picks("gold is at $5,000 and 40 percent up since 1991 for 10 grams of it", size=20)
    check(len(got) <= 2, f"rules: at most 2 highlights on a long page, got {got}")
    got, pages = picks("gold is $5,000 or 40%", size=5)
    check(len(got) == 2, f"rules: 2 highlights on a page of 5 words, got {got}")
    got, pages = picks("up 40% in 1991", size=4)
    check(got == [("40%", "percentage")], f"rules: 1 highlight on a short page, got {got}")

    # the whole flow through group.py and the emphasis.py command line
    src = {"width": 720, "height": 1280, "fps": 30, "durationMs": 9000}
    line = "The gold price is five thousand dollars today. It is up forty percent since 1991 and nobody saw it coming."
    with tempfile.TemporaryDirectory() as tmp:
        wj, cj = Path(tmp) / "words.json", Path(tmp) / "captions.json"
        wj.write_text(json.dumps({"source": src, "language": "en", "words": words(line, 400)}), encoding="utf-8")
        for style in ("glide", "bottom", "keyword", "title"):
            sj = ROOT / "styles" / f"{style}.json"
            subprocess.run([sys.executable, str(ROOT / "scripts" / "group.py"), str(wj), "--style", str(sj), "--out", str(cj)], check=True, capture_output=True)
            cap = json.loads(cj.read_text(encoding="utf-8"))
            flat = [w for p in cap["pages"] for w in p["words"]]
            check(any(w["text"] == "$5,000" and w["emphasis"] and w.get("reason") == "price" for w in flat), f"{style}: '$5,000' is not one highlighted token")
            check(any(w["text"] == "40%" and w["emphasis"] for w in flat), f"{style}: '40%' is not highlighted")
            check(all(w.get("reason") for w in flat if w["emphasis"]), f"{style}: a highlight has no reason")
            check(all(not w["emphasis"] or len(p["words"]) >= 1 for p in cap["pages"] for w in p["words"]), f"{style}: empty page")
            check(all(a["endMs"] <= b["startMs"] for a, b in zip(cap["pages"], cap["pages"][1:])), f"{style}: pages overlap after the hold")
            if style == "keyword":
                check(any(b["text"] in ("$5,000", "40%", "1991") for b in cap.get("big", [])), "keyword: no number among the giant words")
        # Spanish through group.py: the language in words.json picks the rules; pages do not end on "de" or "el"
        line = "Eh, el precio del oro es de cinco mil dólares hoy. Subió un cuarenta por ciento y nadie lo vio venir."
        wj.write_text(json.dumps({"source": src, "language": "es", "words": words(line, 400)}), encoding="utf-8")
        subprocess.run([sys.executable, str(ROOT / "scripts" / "group.py"), str(wj), "--style", str(ROOT / "styles" / "glide.json"),
                        "--out", str(cj), "--clean"], check=True, capture_output=True)
        cap = json.loads(cj.read_text(encoding="utf-8"))
        flat = [w for p in cap["pages"] for w in p["words"]]
        check(any(w["text"] == "$5,000" and w["emphasis"] for w in flat) and any(w["text"] == "40%" and w["emphasis"] for w in flat),
              f"Spanish: '$5,000' and '40%' must be highlighted tokens, got {[w['text'] for w in flat]}")
        check(not any(w["text"].lower().startswith("eh") for w in flat), "Spanish: --clean must drop 'eh'")
        ends = [p["words"][-1]["text"].lower() for p in cap["pages"] if len(p["words"]) > 1]
        check(not any(e in ("el", "del", "de", "un", "y", "lo") for e in ends), f"Spanish: a page ends on a weak word: {ends}")
        wj.write_text(json.dumps({"source": src, "language": "en", "words": words(
            "The gold price is five thousand dollars today. It is up forty percent since 1991 and nobody saw it coming.", 400)}), encoding="utf-8")
        subprocess.run([sys.executable, str(ROOT / "scripts" / "group.py"), str(wj), "--style", str(ROOT / "styles" / "title.json"),
                        "--out", str(cj)], check=True, capture_output=True)
        # picks by hand: one page, by word text; then drop one
        cap = json.loads(cj.read_text(encoding="utf-8"))
        page = next(i for i, p in enumerate(cap["pages"]) if any("nobody" in w["text"] for w in p["words"]))
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "emphasis.py"), str(cj), "--style", "title", "--clear",
                            "--pick", f"{page}:nobody=the surprise", "--show"], capture_output=True, text=True)
        check(r.returncode == 0 and "[nobody]" in r.stdout and "the surprise" in r.stdout, f"emphasis.py --pick failed: {r.stdout} {r.stderr}")
        cap = json.loads(cj.read_text(encoding="utf-8"))
        flagged = [(w["text"], w.get("reason")) for p in cap["pages"] for w in p["words"] if w["emphasis"]]
        check(flagged == [("nobody", "the surprise")], f"emphasis.py --clear --pick left {flagged}")
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "emphasis.py"), str(cj), "--pick", "999:nope=x"], capture_output=True, text=True)
        check(r.returncode != 0, "emphasis.py must refuse a pick on a page that does not exist")
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "emphasis.py"), str(cj), "--drop", f"{page}:nobody"], capture_output=True, text=True)
        cap = json.loads(cj.read_text(encoding="utf-8"))
        check(not any(w["emphasis"] for p in cap["pages"] for w in p["words"]), "emphasis.py --drop did not remove the highlight")

    if failures:
        print("FAILED")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print(f"ok: {len(NUMBERS) + len(SPANISH_NUMBERS) + 9} number cases, rule picks, modes and hand picks passed")


if __name__ == "__main__":
    main()
