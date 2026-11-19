# Subtle

Animated captions and beat-synced lyric videos, rendered locally.

Subtle is a skill for Codex and Claude Code, with a standalone CLI. Give it a video to transcribe and animate
captions in one of 35 styles (39 with the four music styles), or a song to make a lyric video on the beat. It runs on
your machine without uploading the footage or asking for an API key.

**See every style on a real clip: https://subtle.refs.video** (the showcase site runs the same caption engine in the
browser; its source is in `site/`).

![The original 22 styles and the music styles](docs/stills/styles.jpg)

The sheet shows the original set. The newer styles are below, and all of them run live at https://subtle.refs.video.

## Smart highlights

Say "the gold price is five thousand dollars" and the caption shows **$5,000**, highlighted, in one piece.

![Highlighted numbers in four styles](docs/stills/highlights.jpg)

- **The words that matter get the highlight.** Numbers, prices, percentages and dates first, then names and places, then
  the punchline word, then the topic the first time it comes up. Claude reads your captions and picks them, with a
  one-line reason for each that you can read and change. One highlight per page, two on long pages, never filler words.
- **Numbers are written the way you would write them.** "five thousand dollars" and "$5000" become `$5,000`; "forty
  percent" becomes `40%`; "one lakh rupees" becomes `₹1 lakh`; years stay `1991`. An amount is one token: it is never
  split across two lines or two pages. Indian digit grouping (`₹15,00,000`) is used for rupee amounts and Hindi speech.
- **Every style has its own highlight**: a serif italic, a colour, an inverted chip, a second block colour, the giant
  word behind the speaker. A highlighted page also stays on screen a beat longer when there is room.
- **It works with no one picking, too.** Rules find the numbers, names and contrast words (`--emphasis auto`, the
  default). `--emphasis numbers` keeps only numbers, `--emphasis off` turns highlights off, and
  `--emphasis-words 'gold, $5,000'` forces words.

## Lyric videos

Four of the styles are for music: `downbeat`, `billboard`, `chalkline` and `singalong`.

- **On the beat.** Subtle finds the tempo, the beats and the bar lines in the audio (on your machine, no model, no
  key) and starts every page on a beat. Colour flips, pops and cuts follow the beat grid.
- **Your lyrics, the song's timing.** A transcript of singing has the right timing and some wrong words. Pass
  `--lyrics lyrics.txt` (one line per lyric line) and Subtle puts your words on the sung timings and breaks pages
  where your lines break. A chorus you wrote once but that is sung three times stays in, as heard.
- **A song is enough.** Give it an `.mp3` or `.wav` with no picture and it makes the video on a plain canvas
  (`--canvas 9:16`, `16:9`, `1:1` or `4:5`). `singalong:lit` sits over your own footage instead.
- The highlighted word still matters: the biggest word in `billboard`, the underlined one in `chalkline`.

```bash
python3 scripts/subtle.py song.mp3 --style downbeat --lyrics lyrics.txt
python3 scripts/subtle.py song.mp3 --style singalong --lyrics lyrics.txt --canvas 16:9
python3 scripts/subtle.py clip.mp4 --style singalong:lit
```

## Newer in v2

- **Text behind the speaker, per shot.** Six styles (`keyword`, `cover`, `outline`, `poster`, `rise`, `numeral`) put the
  giant word behind the person. Subtle checks every shot on its own: in a wide shot the word goes behind the head, in a
  close-up (where it would be hidden) it is drawn in front or skipped. Needs macOS (Apple Vision cut-out).
- **Smart placement.** Each page moves off the face and the hands, inside the style's allowed range, and only when it has
  to (`--placement auto`, the default; `off` keeps the style's own position).
- **Cut-aware pages.** Hard cuts are found with ffmpeg and no page straddles one (`--cuts auto`; `off` ignores cuts).
- **Automatic legibility.** Subtle measures what is behind every page and adds a soft halo, scrim or outline only where
  the type would not read. Clean dark footage is left untouched (`--legibility auto`; `off` draws the preset as it is).
- **Palette from the footage.** Styles with an accent colour take one that suits the scene and reads on it
  (`--palette auto`; `off` uses the preset's colours).
- **Recipe styles.** One generic style driven by a `recipe` block in the style JSON, so a new caption treatment needs
  no new TSX (see `docs/ARCHITECTURE.md`).

## What it does

1. Transcribes the speech with word-level timing (Whisper large-v3-turbo through `mlx-whisper`).
2. Writes spoken numbers as single tokens (`$5,000`, `40%`, `₹1 lakh`), groups the words into short, readable pages
   and highlights the words that matter.
3. Renders the captions in the style you pick, at the video's own size and frame rate.
4. With a behind-the-speaker style (`keyword`, `cover`, `outline`, `poster`, `rise`, `numeral`), cuts the speaker out with Apple Vision and puts the giant word behind them, shot by shot.
   With a music style, finds the beat and starts every page on it.
5. Moves pages off faces and hands, keeps them clear of cuts, and adds a halo or scrim where the footage would hide the type.
6. Checks the result (safe area, contrast, how much of each big word is visible) and makes a contact sheet.

You get `<name>.captioned.mp4`, `<name>.srt`, `<name>.captions.json` (editable) and `<name>.preview.jpg`.

## Install

**Codex**:

```bash
git clone https://github.com/0xpratzyy/subtle ~/.agents/skills/subtle
```

**Claude Code**:

```bash
git clone https://github.com/0xpratzyy/subtle ~/.claude/skills/subtle
```

Then ask your agent to *"add captions to ~/Movies/talk.mp4"* or *"put a giant keyword behind me"*.
For the standalone CLI, clone the repo anywhere and run the commands below from that directory.

## Requirements

| Need | For | Install |
|---|---|---|
| macOS on Apple Silicon | transcription (`mlx-whisper`) and the behind-the-speaker effect (Apple Vision) | |
| ffmpeg | reading and writing video | `brew install ffmpeg` |
| Node 18 or newer | the caption renderer | `brew install node` |
| Python 3.9 or newer and `uv` | transcription, beats and visual checks | `brew install uv` |
| Swift (Xcode command line tools) | the behind-the-speaker styles and smart placement | `xcode-select --install` |

`bash scripts/doctor.sh` checks all of this and prints what is missing. The first run downloads the speech model (about
1.6 GB) and installs the renderer's packages (about a minute). On Linux or Intel Macs you can still render captions
from your own word timings (`--words`). Run `bash scripts/doctor.sh --from-timings` for this workflow.
Without `uv`, install `mlx-whisper` for transcription and `numpy` and `pillow` for beats and visual checks
in the Python environment that runs Subtle.

## Styles

**22 original caption styles**

|  |  |  |  |
|---|---|---|---|
| ![glide](docs/stills/glide.jpg)<br>**glide** (default)<br>Key words in a large calligraphic script, the small words in bold white sans, on one baseline. | ![glass](docs/stills/glass.jpg)<br>**glass**<br>One frosted-glass pill per page in soft lowercase; upcoming words are dim and brighten as they are spoken. | ![whisper](docs/stills/whisper.jpg)<br>**whisper**<br>Lowercase warm-yellow text; each word is revealed by a soft left-to-right wipe and the page dissolves with a blur. | ![terminal](docs/stills/terminal.jpg)<br>**terminal**<br>Green monospace typed character by character with a blinking block cursor. |
| ![keyword](docs/stills/keyword.jpg)<br>**keyword**<br>One giant pale-lime keyword behind the speaker, the other words small and stacked beside it. | ![accent](docs/stills/accent.jpg)<br>**accent**<br>Pale-lime sans in very short pages, with the key word in a light serif italic; soft fade with a small drift. | ![chip](docs/stills/chip.jpg)<br>**chip**<br>A light rounded chip that hugs the page; words turn from grey to black as they are spoken. | ![title](docs/stills/title.jpg)<br>**title**<br>A typed title whose letter spacing collapses as the letters arrive, with a small handwritten note under it. |
| ![hype](docs/stills/hype.jpg)<br>**hype**<br>A calm medium-weight line in soft white with a gentle shadow; the key word turns warm yellow. Hard cut in, no outline. | ![block](docs/stills/block.jpg)<br>**block**<br>Every line in its own warm coloured block with depth; lines rise in with motion blur and pile up as a stack. | ![impact](docs/stills/impact.jpg)<br>**impact**<br>Heavy round caps; every letter bounces in along an arc with overshoot and a little tilt, on a hard offset shadow. | ![bottom](docs/stills/bottom.jpg)<br>**bottom**<br>Big bold caps low in the frame that build word by word with no animation; the key word is yellow. |
| ![stack](docs/stills/stack.jpg)<br>**stack**<br>A tilted, overlapping pile of words, each at its own size and angle, key words in yellow; the tilt mirrors on alternate pages. | ![serif](docs/stills/serif.jpg)<br>**serif**<br>Display serif italic filled with a top-lit silver gradient; quiet and luxurious. | ![shine](docs/stills/shine.jpg)<br>**shine**<br>Serif italic in one accent colour; a diagonal band of light sweeps across each word, then a soft glow fades. | ![karaoke](docs/stills/karaoke.jpg)<br>**karaoke**<br>The whole line shows dim; each word turns solid as it is spoken. One weight, no motion. |
| ![sticker](docs/stills/sticker.jpg)<br>**sticker**<br>Rounded pink bubbles, one per line, each new line offset to the right of the last and stacked like typed messages; the stack tilts a little more on every page. Words are dark until spoken, then white. | ![ticket](docs/stills/ticket.jpg)<br>**ticket**<br>A hard-edged label tight around the text, tilted a different angle on every page. The hot word sits alone on a big label, filler phrases on a small one. Hard cuts. Colourway: yellow. Also: `ticket:yellow`. | ![highlighter](docs/stills/highlighter.jpg)<br>**highlighter**<br>Bold caps with one flat box behind the word being spoken, hopping from word to word. A finished word turns lime; the hot word comes alone, large. | ![haiku](docs/stills/haiku.jpg)<br>**haiku**<br>One small condensed serif word at a time in acid yellow. Hard cuts, no box. A hot word turns italic and a lighter yellow. |
| ![duo](docs/stills/duo.jpg)<br>**duo**<br>A big condensed caps headline word with a tiny spaced-out lead-in above and a bold italic tail below. The lead-in fades in, the headline cuts in, the tail fades in. | ![editorial](docs/stills/editorial.jpg)<br>**editorial**<br>A bold sans lowercase line with the keyword set about three times larger in a high-contrast italic serif in cinema red, overlapping the sans. Lower-left third. |  |  |

**9 newer styles** (5 go behind the speaker, decided per shot; macOS for the person cut-out)

|  |  |  |
|---|---|---|
| ![cover](docs/stills/cover.jpg)<br>**cover**<br>One huge serif italic word behind the speaker's head, like a magazine masthead; the rest of the line small and tracked in front. | ![outline](docs/stills/outline.jpg)<br>**outline**<br>A giant hollow word behind the speaker that draws on, then fills with colour as it is spoken; a small bold line in front. | ![rise](docs/stills/rise.jpg)<br>**rise**<br>The giant word climbs out from behind the speaker's shoulders letter by letter, and sinks back when the word is done. |
| ![numeral](docs/stills/numeral.jpg)<br>**numeral**<br>Numbers, years and names go giant behind the speaker, digits rolling into place like an odometer; everything else stays small in front. | ![poster](docs/stills/poster.jpg)<br>**poster**<br>Two or three words stacked behind the speaker, each line a different face fitted to the same width, like a film poster's title block. | ![magazine](docs/stills/magazine.jpg)<br>**magazine**<br>A tight justified block like an ad super: keywords in big serif italic, glue words in small grotesk capitals, every line the same width. |
| ![cinema](docs/stills/cinema.jpg)<br>**cinema**<br>Tiny, wide-tracked serif capitals low in the frame that fade in and out slowly, like the subtitles of an arthouse trailer. | ![flip](docs/stills/flip.jpg)<br>**flip**<br>Every letter flips in like a split-flap tile, turning edge-on and settling upright with a motion-blur trail. | ![split](docs/stills/split.jpg)<br>**split**<br>Words alternate to the two sides of the speaker and step down around the head like a staircase, never over the face. |

**4 music / lyric styles** (pages start and move on the beat; see "Lyric videos" below)

|  |  |  |  |
|---|---|---|---|
| ![downbeat](docs/stills/downbeat.jpg)<br>**downbeat**<br>Bold caps on flat colour fields, one to four words a page. Lines spin or slide in with overshoot on the beat; the field flips colour every few bars. | ![billboard](docs/stills/billboard.jpg)<br>**billboard**<br>A fat lowercase serif, one or two words so big they bleed off the frame. Three flat tones swap between text and background; the pair changes every two beats. | ![chalkline](docs/stills/chalkline.jpg)<br>**chalkline**<br>Hand-written lines that write on, left to right, over a dark chalkboard. Lines pile up down the page and indent in steps, then the page clears. The key word is bigger and gets a hand-drawn underline. Variant marker: coloured marker on paper. Also: `chalkline:marker`. | ![singalong](docs/stills/singalong.jpg)<br>**singalong**<br>A block of up to four lyric lines; the sung part of each line fills with a soft colour, letter by letter, as it is sung. Variant lit: no fill, words light up over the picture. Also: `singalong:lit`. |

**4 more speech styles** (newest; no still in this repo, see them at https://subtle.refs.video)

| Style | Looks like |
|---|---|
| `newsroom` | Bold yellow sans, every word on screen at once, the spoken word turns white; soft black outline, lower third. |
| `cards` | White serif on a dark rounded card, the phrase appears at once, key words in red italic. |
| `punch` | Heavy upper-case sans popping in word by word with overshoot; the spoken word swells and turns lime, thick outline. |
| `quiet` | Lowercase medium sans, each line rises gently into place; no box, refined shadow. |

A style is one JSON file in `styles/` plus one small component in `template/src/styles/`. Copy a preset, change the
font, colours, size or timing, and pass its path to `--style`. Some styles have colourways: `--style ticket:yellow`.
`python3 scripts/subtle.py --list-styles` prints them all.

## Use it from the command line

```bash
python3 scripts/subtle.py talk.mp4                          # glide
python3 scripts/subtle.py talk.mp4 --style glass            # frosted-glass pill
python3 scripts/subtle.py talk.mp4 --style keyword          # a giant keyword behind the speaker
python3 scripts/subtle.py talk.mp4 --style cover --legibility off --palette off   # behind a headline, preset colours
python3 scripts/subtle.py talk.mp4 --style ticket:yellow    # a colourway of a style
python3 scripts/subtle.py song.mp3 --style downbeat --lyrics lyrics.txt   # a lyric video on the beat
python3 scripts/subtle.py talk.mp4 --style accent --emphasis-words 'gold, $5,000' --vocab "Meera, RBI"
python3 scripts/subtle.py talk.mp4 --emphasis numbers       # highlight only numbers, prices, percentages and years
python3 scripts/subtle.py talk.mp4 --hinglish               # Hindi written in Latin letters
python3 scripts/subtle.py talk.mp4 --aspect 9:16            # centre-crop first
python3 scripts/subtle.py talk.mp4 --placement off --cuts off   # keep the style's own position, ignore cuts
python3 scripts/subtle.py talk.mp4 --behind off             # draw giant words in front, never behind
python3 scripts/subtle.py talk.mp4 --captions talk.captions.json   # re-render after editing the captions
```

The transcript is cached by the file's hash, so trying another style does not transcribe again.

## Limits

- The behind-the-speaker effect (`keyword`, `cover`, `outline`, `poster`, `rise`, `numeral`) works best with one person and a steady camera. Fine hair, fast hand
  movement and fast pans show at the matte edge. Subtle checks the subject first and draws the words in front when it
  would look bad.
- Styles without a container (soft-shadow text) can be hard to read on bright or busy footage; the check warns about
  low contrast and suggests `glass`, `chip` or `block`.
- Whisper spells Hindi words in Latin letters unevenly. Read the transcript before rendering and fix words with
  `--replace heard=Shown`.
- Music styles need a clear pulse. On speech or ambient music Subtle says it found no steady beat and the pages
  follow the words. Bar lines assume 4/4. Whisper hears sung words less well than spoken ones: use `--lyrics`.
- A giant number is never put behind the speaker in `keyword` (hidden digits would change it): it is drawn in front. `numeral` is built for numerals behind the speaker.
- Word timings come from Whisper's attention, not forced alignment. They are usually within a frame or two; very fast
  speech can drift.

## Licences

Subtle's code is MIT. The bundled fonts are under the SIL Open Font License. The default renderer uses
[Remotion](https://www.remotion.dev), which is free for individuals and companies of up to 3 people; larger companies
need a Remotion company licence. Details for every dependency are in [THIRD_PARTY.md](THIRD_PARTY.md).

The showcase site (`site/`) uses a third-party clip for demo only. That media is not in this repo; see
[site/README.md](site/README.md) for how to make your own.

How the pieces fit together: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

Made by [Refs](https://refs.video).
