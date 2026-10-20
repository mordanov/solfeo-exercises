# Image-generation prompt: evolving magical-animal avatars

Use with an image model (OpenAI image or similar). Replace `{ANIMAL}` and run once per animal. Start with ONE animal (e.g. dragon), check style and growth, then do the rest.

Tips:
- 8 animals × 30 images = 240 images.
- Keep the best reference sheet and use it as the first reference when generating other animals, so all animals share one style.
- If stages 08-10 look too scary, strengthen "friendly hero" and "cartoon" in the prompt.
- File names match the main prompt convention: `assets/avatars/{animal_id}/{stage}_{mood}.png`, stage zero-padded 01..10.

---

```
# TASK
Create a set of cartoon character images for a children's music game (audience: kids 6-9). One magical animal character evolves through 10 growth stages, from a cute baby in a diaper to a huge, muscular, serious adult. Each stage needs 3 moods: neutral, happy, sad. Total per animal: 30 images.

# ANIMAL
{ANIMAL}  (one of: unicorn, dragon, phoenix, griffin, sphinx cat, kitsune fox, pegasus, mermaid)

# GLOBAL STYLE (identical for every image of every animal)
- Very cartoonish children's-game illustration: bold thick dark-brown outlines, flat colors with soft cel-shading, rounded shapes, big expressive eyes, chunky proportions, high saturation, candy-like palette.
- Same line weight, same shading style, same lighting (soft light from top-left) across all stages and moods.
- ONE single character, full body, centered, facing 3/4 front, standing on nothing (no ground, no shadow plate).
- Square canvas 1024x1024, transparent background (PNG). Character fills about 80% of the height with equal margins; keep the same framing and baseline for all stages so the character grows in size and mass only through its design.
- No text, no letters, no numbers, no frames, no badges, no borders, no watermarks, no logos. (The app draws frames, level badges and prefixes itself.)
- No copyrighted or franchise characters, no real people, no brand look-alikes.

# CHILD-SAFETY RULES FOR "BRUTAL" STAGES
"Brutal" means STRONG and SERIOUS in a cartoon-hero way, never violent or scary: no weapons, no blood, no wounds, no scars, no gore, no skulls, no fangs dripping, no menacing or horror expression, no nudity beyond a cartoon diaper at the baby stages. Strength is expressed through big muscles, broad posture, heavy brows, stern determined face, heroic pose, and tasteful gear (belts, bracers, capes, armor plates, glowing accessories). The character must always still look like a hero a child would admire.

# CHARACTER CONSISTENCY
- Define the species identity first (signature colors, horn/wing/tail/mane shape, markings, eye color). Keep these identical at every stage: color palette, markings, signature feature, eye color.
- Each stage must be recognisably the SAME individual grown up: reuse the same markings and colors; the face gradually matures.
- Body proportions by stage: baby = huge head, tiny body (about 2 heads tall); gradually toward athletic (about 5 heads tall) and heroic muscular (about 6-7 heads tall) at the top stages.

# 10 STAGES (neutral mood description; apply mood rules below on top)
01 ути-пути: a newborn baby version, tiny round body, giant head, huge sparkling eyes, stubby limbs, tiny nubs of the species' signature feature (small horn/wings/tail), wearing a big white cloth diaper, holding a pacifier or baby bottle. Pure cuteness.
02 микро: a crawling or toddling baby, still in a diaper but now with a cute tiny bib or a tiny hat, small signature features visible, curious eyes, clumsy cute pose.
03 мини: a small kid, no diaper, wearing a tiny colorful t-shirt or shorts, small backpack or a toy, bright cheerful face, standing on two or four legs as natural for the species.
04 настоящий: a teenage version, slim and energetic, signature features fully formed but small, a sporty bandana or scarf, confident smile, first hint of athletic build.
05 супер: a young hero, athletic and fit, defined but slim muscles, a small superhero cape, brave determined smile, signature features clearly impressive.
06 мега: a strong adult, visibly muscular, broad chest and shoulders, a bold sleeveless outfit or vest, bracers, confident smirk, strong heroic stance.
07 убер: a very muscular adult, big arms and chest, stern focused face, heavy brows, armor shoulder pads and a wide belt, signature features larger and more detailed (bigger horn/wings/tail), powerful pose.
08 великий: a huge bodybuilder-like heroic adult, massively muscular, serious expression, proud posture, ornate cartoon armor pieces and a flowing cape, signature features grand and glowing slightly.
09 величайший: a colossal legendary champion, extremely muscular, very serious and noble face, golden armor accents, glowing energy aura around signature features, majestic heroic pose, looks like a legend.
10 божественный: a divine titan, the strongest and most imposing version, massively muscular, calm stern powerful face, radiant golden halo or celestial crown, glowing cosmic aura (stars, soft light rays), regal cape and divine gold-white armor, the pinnacle of strength while remaining a friendly hero.

Species adaptation notes (apply only when relevant):
- mermaid: replace diaper with a tiny cloth/shell wrap at the baby stages; strong stages use a powerful tail, muscular upper body, shell/pearl armor, trident-free (no weapons).
- phoenix: baby is a fluffy chick in a diaper; later stages gain bigger flaming feathers (cartoon flames, soft glow, not scary).
- sphinx cat, fox, griffin, dragon, unicorn, pegasus: keep natural anatomy, anthropomorphic muscular posture allowed at upper stages.

# 3 MOODS (apply to every stage; keep pose, outfit, size and framing IDENTICAL, change only the face and slight posture)
- neutral: calm, friendly default face (for strong stages: serious and focused).
- happy: big joyful expression, wide open smile, sparkling eyes, small sparkles near the character. For strong stages: proud confident grin, not silly.
- sad: gentle disappointed expression, drooping eyes, one small cartoon tear at most, slightly lowered head or ears. For strong stages: stoic, slightly crestfallen, never crying hard. Always sympathetic, never distressing.

# GENERATION WORKFLOW (follow strictly to stay consistent)
1. Generate a character reference sheet for {ANIMAL}: one image with the signature colors and features, used to lock the identity.
2. Generate stage 01 neutral using the reference sheet as reference.
3. Generate stages 02 -> 10 neutral one after another, each using the previous stage AND the reference sheet as references.
4. For every stage, generate happy and sad by editing that stage's neutral image (change only the face and slight posture, keep everything else pixel-consistent).
5. Review: the full row of 10 neutral images must read as one character growing up; mood variants must match their neutral image.

# OUTPUT
Files named {animal_id}/{stage}_{mood}.png where stage is zero-padded 01..10 and mood is neutral|happy|sad, e.g. unicorn/01_neutral.png, dragon/10_sad.png. Use lowercase animal ids: unicorn, dragon, phoenix, griffin, sphinx_cat, kitsune_fox, pegasus, mermaid.
```
