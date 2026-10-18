# PlayMate — Gemini image prompts

Prompts for PlayMate's avatars, profile banners and match-card backgrounds.
Paste them into Gemini (the image model) **in English**, one per message.

## How to use

1. Open a **new Gemini chat** and send the **Style guide** below first, with this line on top:
   `Remember this style guide and apply it to every image I ask for in this chat. Reply "OK".`
2. Then send prompts one by one. Each prompt already repeats the key style words, so it also works in a fresh chat.
3. **Aspect ratio:** say it in the message too (Gemini sometimes ignores it inside a long prompt):
   avatars **1:1**, banners **21:9**, card backgrounds **3:4**.
4. Generate 2–4 versions of each and keep the best one. If something is off, reply with a short fix
   ("less busy background", "face more centered", "no text") instead of rewriting the whole prompt.
5. **Save as PNG** with these names and put them in one folder, then tell me where it is. I'll resize, convert to WebP
   and wire them in:
   - `avatar-13.png`, `avatar-14.png`, … (1:1, ideally 1024×1024)
   - `banner-9.png`, `banner-10.png`, … (21:9, ideally ≥ 2016×864)
   - `card-<theme>.png` (3:4, ideally 1200×1600)

> ⚠️ **No real game characters, logos or names.** Everything must be original "inspired by the genre" art — this keeps
> PlayMate safe legally and Gemini will refuse or water down prompts that name real characters. Don't add game titles,
> UI, watermarks or any text inside the images.

---

## Style guide (send this first)

```
PlayMate visual style guide:
- Brand: PlayMate, a teammate-finder for gamers. Mood: competitive but friendly, premium, modern esports.
- Look: dark sci-fi "neon + glass". Deep near-black navy backgrounds (#070b10 to #121b25), with glowing neon accents in
  mint green (#2dffb3), electric cyan (#2ee6ff) and lime (#b6ff5c). Each image may add ONE extra accent color that fits
  its theme (orange, purple, red, gold, pink or blue).
- Rendering: high-quality digital illustration, semi-realistic stylized 3D look (like a modern game key art or esports
  team poster), clean shapes, crisp rim lighting, soft volumetric glow, subtle film grain. Not photorealistic, not
  cartoon-childish, not anime-chibi.
- Composition: strong single focal point, uncluttered, readable at small sizes, plenty of dark negative space.
- Always: no text, no letters, no numbers, no logos, no watermarks, no UI, no real brands, no real game characters,
  no real people, no gore, no blood, no weapons pointed at the viewer.
```

---

## 1. Avatars (profile pictures) — 1:1

Shown as a **small circle (≈100–140 px)**, so they must read clearly when tiny: one character, head-and-shoulders,
centered, simple background.

**Base (add to the start of every avatar prompt if you're not in the style-guide chat):**
`Square 1:1 profile avatar for a gaming app, head-and-shoulders portrait, centered with the face in the middle third, works when cropped to a circle, dark navy background with a soft neon glow behind the head, crisp rim light, stylized semi-realistic 3D illustration, no text, no logos.`

| File | Prompt |
|---|---|
| avatar-13 | A tactical soldier in a modern combat helmet with a flip-up night-vision mount and a scarf, determined look, orange rim light from burning city glow behind, mint green accent light on the visor. |
| avatar-14 | A battle-royale skydiver with goggles pushed up on the forehead and a grin, wind-blown hair, parachute straps on shoulders, purple and cyan sky glow. |
| avatar-15 | A futuristic arena legend with a sleek armored collar and a glowing cyan holographic eyepiece, confident smirk, red accent lights. |
| avatar-16 | A calm sniper with a hooded ghillie-style cloak and a single glowing green lens over one eye, mysterious, mostly in shadow. |
| avatar-17 | A friendly field medic with a helmet marked by a simple glowing plus-shaped light (no text), headset microphone, warm smile, mint accent. |
| avatar-18 | A fantasy battle mage with glowing runes floating around their hands near the chin, hood with gold trim, violet and cyan magic light. |
| avatar-19 | A heavily armored knight-warrior with a sleek futuristic helmet, glowing visor slit, ember sparks, gold accent. |
| avatar-20 | A street racer in a padded racing jacket and a helmet tucked under the arm (no brand marks), neon city lights reflected, blue and pink accents. |
| avatar-21 | A football (soccer) player in a plain unbranded jersey with a short beard, stadium floodlight bokeh behind, teal accent, confident pose. |
| avatar-22 | A stylish getaway-driver character with sunglasses and a gold chain, palm-tree sunset glow behind, pink and orange accent. |
| avatar-23 | A space trooper in a bulky sci-fi armored helmet with a yellow glowing visor, dust and sparks, heroic, from a co-op alien-war mood. |
| avatar-24 | A cyber hacker with a glowing neon-green visor and a hoodie, code-like light streaks (abstract, no readable characters). |
| avatar-25 | A cute but cool robot gamer mascot with round LED eyes and gaming headphones, mint glow. |
| avatar-26 | A fox mascot wearing gaming headphones, sly smile, orange fur with cyan rim light, esports team-mascot style. |
| avatar-27 | A wolf mascot with glowing cyan eyes and a tactical vest, esports team-mascot style, fierce but friendly. |
| avatar-28 | A blocky voxel-style adventurer made of cubes holding a tiny glowing pickaxe, mint and lime light (original character, not from any game). |
| avatar-29 | A woman gamer with short undercut hair and a mic headset, focused expression, cyan monitor light on her face. |
| avatar-30 | A man gamer with braided hair and an over-ear headset, laughing, lime and mint light, relaxed pose. |

Tip: keep **variety** — different skin tones, genders and ages across the set, and some non-human avatars for
players who don't want a "face".

---

## 2. Profile banners — 21:9

Shown **full width at the top of the profile, about 220 px tall**. On phones the sides get cropped and the bottom
fades to dark, and the round avatar overlaps the **bottom-left**. So: keep the subject in the **center**, keep the
**bottom third calm and dark**, keep the left-bottom corner empty.

**Base (add to the start of every banner prompt if you're not in the style-guide chat):**
`Ultra-wide 21:9 profile banner for a gaming app, cinematic key-art landscape, main subject in the center, the bottom third darker and calmer for text overlay, empty space at bottom-left, dark navy tones with neon glow, stylized semi-realistic 3D illustration, no characters' faces close-up, no text, no logos.`

| File | Theme | Prompt |
|---|---|---|
| banner-9 | Large-scale war | A massive modern battlefield at dusk: distant ruined city skyline, helicopters silhouetted against orange smoke, tanks rolling across a ridge, tracer light streaks, embers in the air. |
| banner-10 | Tactical shooter | A tense desert-town bomb-site at sunset: sandstone walls, a narrow archway, two silhouetted operators holding angles, dust in warm light, gold accent. |
| banner-11 | Battle royale | Players gliding down from a bright purple storm sky toward a colorful island with floating build ramps, a glowing storm wall circle on the horizon. |
| banner-12 | Sci-fi arena BR | A futuristic canyon arena with jump towers and a dropship overhead, red and cyan light, small squad silhouettes on a cliff edge. |
| banner-13 | Mobile BR | An aerial view of an island at golden hour with several parachutes drifting down, a cargo plane trail, loot crates glowing on the ground. |
| banner-14 | Fast shooter | A rain-soaked night city street with neon reflections, two silhouetted soldiers advancing, green and cyan light, motion streaks. |
| banner-15 | Sandbox / voxel | A giant blocky voxel landscape at sunrise: cube mountains, a waterfall, a small cube castle, mint and lime glowing ore crystals (original style). |
| banner-16 | MOBA fantasy | A glowing fantasy battle lane between two crystal towers, magical energy beams, a jungle valley in the distance, violet and cyan light. |
| banner-17 | Co-op sci-fi war | Four armored space troopers silhouetted on an alien ridge as drop pods streak down from a stormy orange sky, bug-like creatures in the distance. |
| banner-18 | Football | A packed football stadium at night from pitch level: floodlights flaring, light haze, a ball on the center spot, teal and white light. |
| banner-19 | Open-world crime | A neon coastal city at sunset with palm trees, a glossy sports car on the highway, pink and orange sky, retro-wave mood. |
| banner-20 | Car soccer | A futuristic indoor car-soccer arena: rocket-boosted cars flying with blue and orange trails toward a giant glowing ball. |
| banner-21 | Generic — squad | Silhouettes of five gamers of different styles standing together on a glowing neon platform, looking at a distant skyline, mint and cyan rim light (team spirit). |
| banner-22 | Generic — setup | A dark gaming room with an ultra-wide glowing monitor, a headset on the desk, RGB light reflecting off glass, cozy and premium. |
| banner-23 | Generic — abstract | Abstract flowing neon light ribbons in mint, cyan and lime over a deep navy grid, subtle hexagon pattern, energetic but clean. |
| banner-24 | Generic — night city | A cyberpunk skyline at night viewed from a rooftop, holographic billboards with abstract shapes (no text), cool cyan haze. |

---

## 3. Match-card backgrounds ("card styles") — 3:4

Subtle textures behind the **player card** on the Find-match screen. Text and icons sit on top, so these must be
**dark, low-contrast and quiet in the middle**, with the interesting detail only at the edges/corners. Later these can
become unlockable card skins.

**Base (add to the start of every card prompt):**
`Vertical 3:4 background texture for a gaming player card, very dark and low contrast in the center so white text stays readable, decorative detail only near the edges and corners, subtle neon glow, premium esports trading-card feel, no characters, no text, no logos.`

| File | Prompt |
|---|---|
| card-neon | Thin mint and cyan neon circuit lines tracing the border with a soft glow in the corners, faint hexagon grid. |
| card-ember | Glowing orange embers and smoke drifting up from the bottom edge, charcoal center, war-zone mood. |
| card-storm | Purple storm energy crackling along the edges, faint lightning veins, deep violet-black center. |
| card-frost | Icy cyan crystal shards growing in from the corners, cold mist, frosted-glass center. |
| card-gold | Elegant gold filigree corners with a subtle glow, black velvet center — "legendary" rarity look. |
| card-pitch | Faint football-pitch lines and floodlight glare at the top, dark green-black center. |
| card-sunset | Retro-wave sunset stripes and palm silhouettes only at the bottom edge, dark magenta-navy center. |
| card-cosmic | A starfield with a soft nebula glow around the edges, near-black center, tiny shooting star in a corner. |

---

## 4. Optional extras (if you have time)

- **Landing hero image (16:9):** `A group of diverse gamers in a dark neon room high-fiving across glowing screens, mint and cyan light, cinematic, joyful, original characters, no text, no logos.`
- **Social share image (1.91:1, 1200×630):** `Abstract neon squad emblem made of four glowing connected nodes forming a diamond, deep navy background, mint, cyan and lime light, lots of empty space on the left for a title, no text.`
- **Empty-state illustration (1:1):** `A lonely gamer silhouette with a headset sitting on a glowing platform, looking at an empty seat beside them, soft mint light, hopeful mood, minimal, no text.`

## Quality checklist before sending me the files

- [ ] No text/letters/logos anywhere (zoom in — models like to sneak in fake letters).
- [ ] Avatars still readable when shrunk to a 100 px circle.
- [ ] Banners: subject centered, bottom third calm, bottom-left corner empty.
- [ ] Card backgrounds: center is dark enough for white text.
- [ ] Colors match the brand (dark navy + mint/cyan/lime + one accent).
