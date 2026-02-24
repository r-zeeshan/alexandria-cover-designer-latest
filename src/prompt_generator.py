"""Phase 1B — Prompt engineering for 99 books × 5 variants."""

from __future__ import annotations

import argparse
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from src import safe_json
    from src.logger import get_logger
except ModuleNotFoundError:  # pragma: no cover
    import safe_json  # type: ignore
    from logger import get_logger  # type: ignore

logger = get_logger(__name__)

DEFAULT_CATALOG_PATH = Path("config/book_catalog.json")
DEFAULT_TEMPLATES_PATH = Path("config/prompt_templates.json")
DEFAULT_OUTPUT_PATH = Path("config/book_prompts.json")

REQUIRED_PHRASE_COMPOSITION = "circular vignette composition"
REQUIRED_PHRASE_TEXT = "no text, no letters, no words, no watermarks"
REQUIRED_PHRASE_NO_FRAME = (
    "no border, no frame, no decorative edge, no ornamental border, interior scene only, edge to edge"
)

VARIATION_DIRECTIVES = [
    "",
    "Use a warm palette with amber and antique gold tones.",
    "Use a cool palette with deep blue and silver accents.",
    "Emphasize dramatic chiaroscuro lighting and strong contrast.",
    "Render with muted aged-canvas texture and restrained saturation.",
    "Emphasize intricate fine detail and delicate linework.",
    "Use rich jewel tones with emerald, ruby, and sapphire accents.",
    "Render in a loose impressionistic brushwork style.",
    "Use earthy sienna, umber, and ochre with naturalistic light.",
    "Create a moody atmospheric composition with soft depth.",
    "Use bold graphic silhouettes and high-contrast value shapes.",
]


@dataclass
class BookPrompt:
    """One generated prompt variant for one book."""

    book_number: int
    book_title: str
    book_author: str
    variant_id: int
    variant_key: str
    variant_name: str
    description: str
    prompt: str
    negative_prompt: str
    style_reference: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "variant_key": self.variant_key,
            "variant_name": self.variant_name,
            "description": self.description,
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "style_reference": self.style_reference,
            "word_count": _word_count(self.prompt),
        }


@dataclass
class BookMotif:
    """Visual motif pack for one title."""

    iconic_scene: str
    character_portrait: str
    setting_landscape: str
    dramatic_moment: str
    symbolic_theme: str
    style_specific_prefix: str = "woodcut allegorical tableau"


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _word_count(text: str) -> int:
    return len(text.split())


def _limit_words(text: str, max_words: int = 24) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    trimmed = words[:max_words]
    while trimmed and trimmed[-1].lower().strip(",.;:") in {
        "and",
        "or",
        "with",
        "of",
        "the",
        "a",
        "an",
        "to",
        "toward",
        "towards",
    }:
        trimmed = trimmed[:-1]
    return " ".join(trimmed)


def _strip_forbidden(text: str, title: str, author: str) -> str:
    # Prevent direct mention of full title/author strings in prompts.
    for forbidden in (title.strip(), author.strip()):
        if not forbidden or len(forbidden) < 4:
            continue
        pattern = re.compile(rf"\b{re.escape(forbidden)}\b", flags=re.IGNORECASE)
        text = pattern.sub("the story", text)
    return text


def _ensure_prompt_constraints(prompt: str) -> str:
    prompt = re.sub(r"\s+", " ", prompt).strip().rstrip(",")
    low = prompt.lower()

    if REQUIRED_PHRASE_COMPOSITION not in low:
        prompt += f", {REQUIRED_PHRASE_COMPOSITION}"
        low = prompt.lower()
    if REQUIRED_PHRASE_TEXT not in low:
        prompt += f", {REQUIRED_PHRASE_TEXT}"
        low = prompt.lower()
    if "no border" not in low and "no frame" not in low:
        prompt += f", {REQUIRED_PHRASE_NO_FRAME}"

    while _word_count(prompt) < 40:
        prompt += ", warm cinematic atmosphere, balanced composition, intricate period detail"

    if _word_count(prompt) > 80:
        prompt = " ".join(prompt.split()[:80]).rstrip(",")

    return prompt


def enforce_prompt_constraints(prompt: str) -> str:
    """Public wrapper used by runtime generation paths."""
    return _ensure_prompt_constraints(prompt)


def diversify_prompt(base_prompt: str, variant_index: int) -> str:
    """Inject style variation directives so variants are meaningfully distinct."""
    text = re.sub(r"\s+", " ", str(base_prompt or "")).strip()
    if not text:
        return text
    token = max(0, int(variant_index) - 1)
    directive = VARIATION_DIRECTIVES[token % len(VARIATION_DIRECTIVES)].strip()
    if not directive:
        return text
    return f"{text} {directive}".strip()


def _motif_for_book(book: dict[str, Any]) -> BookMotif:
    title = _normalize(book.get("title", ""))
    author = _normalize(book.get("author", ""))
    title_author = f"{title} {author}"

    if "moby dick" in title_author or "whale" in title_author:
        core = "Captain Ahab, white whale, stormy sea, splintering whaling ship, violent spray"
        return BookMotif(
            iconic_scene=core,
            character_portrait="Captain Ahab with ivory leg on a rain-lashed deck, white whale looming across stormy sea",
            setting_landscape="the Pequod crossing black sea swells beneath thunderheads, white whale wake trailing beside Captain Ahab's hunt",
            dramatic_moment="Captain Ahab hurling a final harpoon as the white whale erupts through stormy sea and shattered masts",
            symbolic_theme="obsession consuming Captain Ahab beneath a colossal white whale shadow over a furious stormy sea",
            style_specific_prefix="storm-lit symbolic woodcut",
        )
    if "alice" in title_author and "wonderland" in title_author:
        core = "rabbit hole descent, mad tea party table, Queen of Hearts court, surreal garden labyrinth"
        return BookMotif(
            iconic_scene=core,
            character_portrait="curious young girl in blue dress navigating rabbit hole tunnels toward a mad tea party and Queen of Hearts banners",
            setting_landscape="dreamlike chessboard garden where rabbit hole paths lead to a mad tea party beneath Queen of Hearts roses",
            dramatic_moment="chaotic card soldiers charging from the Queen of Hearts court as a rabbit hole portal tears open beside the tea party",
            symbolic_theme="curiosity confronting absurd authority through rabbit hole spirals, shattered tea party clocks, and Queen of Hearts emblems",
            style_specific_prefix="surreal ink-wash allegorical tableau",
        )
    if "dracula" in title_author:
        core = "vampire stalking moonlit battlements of a Transylvanian castle above misted forest"
        return BookMotif(
            iconic_scene=f"{core}, torchlit crypts, red moon",
            character_portrait="aristocratic vampire with pale gaze on a Transylvanian castle balcony, wolves and fog below",
            setting_landscape="looming Transylvanian castle perched over ravines, chapel ruins, and swirling bats under winter moonlight",
            dramatic_moment="vampire advancing through candlelit crypt corridors as dawn strikes a Transylvanian castle stained-glass tower",
            symbolic_theme="predatory immortality symbolized by a vampire silhouette eclipsing a Transylvanian castle over blood-red mist",
            style_specific_prefix="gothic chiaroscuro woodcut",
        )
    if "pride and prejudice" in title_author:
        core = "Regency era courtship in an English countryside estate ballroom with candlelight and social tension"
        return BookMotif(
            iconic_scene=core,
            character_portrait="a poised Regency-era gentlewoman and a reserved gentleman framed by an English countryside manor ballroom",
            setting_landscape="rolling English countryside, grand manor facade, and illuminated Regency-era ballroom windows at dusk",
            dramatic_moment="heated proposal exchange on a rain-dark terrace above an English countryside ballroom during the Regency era",
            symbolic_theme="class expectation versus desire shown through mirrored Regency-era dancers in an English countryside ballroom",
            style_specific_prefix="Regency-era watercolor engraving fusion",
        )
    if "frankenstein" in title_author or "modern prometheus" in title_author:
        core = "the creature awakening in a candlelit laboratory as lightning forks through high windows"
        return BookMotif(
            iconic_scene=core,
            character_portrait="the creature, stitched and sorrowful, lit by laboratory coils and violent lightning shadows",
            setting_landscape="alpine laboratory tower above storm clouds, cracked instruments, and lightning illuminating frozen peaks",
            dramatic_moment="the creature confronting its creator amid shattered laboratory glass while lightning ignites the night sky",
            symbolic_theme="human ambition fractured by conscience, represented by the creature before a laboratory halo of lightning",
            style_specific_prefix="expressionist woodcut etching",
        )
    if "christmas carol" in title_author:
        return BookMotif(
            iconic_scene="a miser guided through snowy Victorian streets by a luminous spirit above clock towers",
            character_portrait="an elderly businessman in frosted nightcoat, haunted by ghostly light in a Victorian doorway",
            setting_landscape="snowy Victorian London lanes, gas lamps, church spires, and warm windows in winter fog",
            dramatic_moment="spirit-led revelation over a gravestone in swirling snow as dawn breaks over Victorian rooftops",
            symbolic_theme="redemption symbolized by an icy heart thawing into candlelit generosity over winter streets",
            style_specific_prefix="festive etching with watercolor wash",
        )
    if "crime and punishment" in title_author:
        return BookMotif(
            iconic_scene="a guilt-ridden student wandering a cramped Petersburg alley after a violent moral transgression",
            character_portrait="gaunt young intellectual under a streetlamp, restless eyes, fevered expression, threadbare coat",
            setting_landscape="narrow Petersburg courtyards, wet cobblestones, oppressive tenement walls, and pale dawn haze",
            dramatic_moment="confession in a crowded police office as rain-streaked windows trap the city in gray light",
            symbolic_theme="conscience as a split shadow stalking a lone figure through labyrinthine streets and church domes",
            style_specific_prefix="psychological charcoal-etch hybrid",
        )
    if "romeo and juliet" in title_author:
        return BookMotif(
            iconic_scene="moonlit balcony meeting between rival houses in Renaissance Verona with tense guards below",
            character_portrait="young lovers in Renaissance attire, longing expressions, candlelight and danger in the courtyard",
            setting_landscape="Verona rooftops, cypress silhouettes, stone arches, and lantern-lit piazza at twilight",
            dramatic_moment="desperate final embrace in a candlelit crypt amid roses and cold marble",
            symbolic_theme="love against feud shown as intertwined roses crossing two drawn blades",
            style_specific_prefix="Renaissance tempera-style allegory",
        )
    if "journey to the centre of the earth" in title_author:
        return BookMotif(
            iconic_scene="expedition crossing a subterranean sea beneath colossal crystal caverns and volcanic arches",
            character_portrait="determined explorer with lantern and rope map, soot-streaked face, awe before underground giants",
            setting_landscape="vast caverns of glowing minerals, ancient forests, and distant prehistoric silhouettes",
            dramatic_moment="raft hurled toward a volcanic shaft as molten light and steam engulf the cavern",
            symbolic_theme="human curiosity represented by a tiny lantern descending spiral strata toward primal fire",
            style_specific_prefix="adventure lithograph tableau",
        )
    if "twenty thousand leagues" in title_author:
        return BookMotif(
            iconic_scene="a sleek submarine gliding past giant squid and ruined statues in midnight blue depths",
            character_portrait="stoic sea captain in ornate coat within brass-lit control room, ocean pressure beyond glass",
            setting_landscape="abyssal seascape with coral cathedrals, volcanic vents, and bioluminescent currents",
            dramatic_moment="submarine struck by a giant squid as lightning flashes across storm waves above",
            symbolic_theme="isolation and wonder symbolized by a lone vessel encircled by abyssal light",
            style_specific_prefix="nautical copperplate allegory",
        )
    if "prince and the pauper" in title_author:
        return BookMotif(
            iconic_scene="two identical boys exchanging garments in a crowded Tudor marketplace",
            character_portrait="noble youth and street child facing each other, mirrored expressions, contrasting fabrics",
            setting_landscape="Tudor London lanes, palace towers, and bustling market stalls under gray sky",
            dramatic_moment="public coronation turmoil as hidden identity is revealed before astonished court",
            symbolic_theme="class inversion symbolized by a split crown above worn shoes and velvet slippers",
            style_specific_prefix="Tudor woodcut narrative plate",
        )
    if "invisible man" in title_author:
        return BookMotif(
            iconic_scene="bandaged figure in a provincial inn, objects levitating as townsfolk recoil",
            character_portrait="faceless man wrapped in cloth and dark goggles, tense posture, winter coat",
            setting_landscape="windswept village street with blown papers and open doors revealing disturbed interiors",
            dramatic_moment="chaotic pursuit through snow as footprints race without a visible body",
            symbolic_theme="unchecked intellect symbolized by empty clothing collapsing beneath cold light",
            style_specific_prefix="grotesque monochrome etching",
        )
    if "time machine" in title_author:
        return BookMotif(
            iconic_scene="inventor operating brass chronometer in a Victorian laboratory as time blurs around him",
            character_portrait="Victorian scientist with soot-streaked waistcoat, focused gaze, mechanical controls in hand",
            setting_landscape="ruined future city beneath red twilight, broken statues, and overgrown marble steps",
            dramatic_moment="descent into subterranean tunnels where pale creatures surround a flickering machine",
            symbolic_theme="progress and decay represented by a clock face split between roses and rusted gears",
            style_specific_prefix="retro-futurist etching plate",
        )
    if "jungle book" in title_author:
        return BookMotif(
            iconic_scene="wolf-raised child moving through moonlit jungle beside panther and bear companions",
            character_portrait="young forest boy poised with staff, alert gaze, tiger-striped shadows behind",
            setting_landscape="dense tropical canopy, river bend, ruined temples, and monsoon clouds",
            dramatic_moment="fire confrontation with a tiger at the edge of a storm-lit clearing",
            symbolic_theme="belonging and instinct shown by human footprints merging with animal tracks",
            style_specific_prefix="lush watercolor-etch fusion",
        )
    if "robinson crusoe" in title_author:
        return BookMotif(
            iconic_scene="shipwreck survivor building shelter beside palms and broken timbers on a remote shore",
            character_portrait="bearded castaway with handmade tools, weathered clothes, vigilant horizon gaze",
            setting_landscape="lonely island cove, steep cliffs, driftwood, and a distant storm at sea",
            dramatic_moment="first encounter with an ally marked by footprints in wet sand at dawn",
            symbolic_theme="self-reliance represented by a solitary fire against endless ocean",
            style_specific_prefix="maritime wood engraving",
        )
    if "hamlet" in title_author:
        return BookMotif(
            iconic_scene="brooding prince in a torchlit hall holding a skull under northern night",
            character_portrait="melancholic royal in black attire, sharp profile, spectral light across his face",
            setting_landscape="windswept Danish battlements, icy sea horizon, and banners under moonlight",
            dramatic_moment="duel in a crowded court as poisoned steel flashes beneath chandeliers",
            symbolic_theme="indecision and fate represented by a cracked crown beside an hourglass",
            style_specific_prefix="tragic chiaroscuro engraving",
        )
    if "oedipus" in title_author:
        return BookMotif(
            iconic_scene="troubled king before temple steps as plague-stricken citizens plead for relief",
            character_portrait="tormented ruler in Greek robes, laurel crown askew, eyes shadowed by prophecy",
            setting_landscape="ancient Theban gates, marble columns, and dry hills under harsh sun",
            dramatic_moment="horrific revelation in palace court with torn garments and fallen scepter",
            symbolic_theme="fate represented by a blindfolded figure beneath a broken royal seal",
            style_specific_prefix="classical fresco-inspired woodcut",
        )
    if "dorian gray" in title_author:
        return BookMotif(
            iconic_scene="young aesthete facing an unsettling portrait in candlelit studio",
            character_portrait="refined gentleman in velvet coat, beautiful surface hiding moral corruption",
            setting_landscape="opulent London salon with mirrors, drapery, and covered canvases",
            dramatic_moment="portrait unveiled during thunder as hidden decay erupts into view",
            symbolic_theme="beauty versus guilt represented by a gilded frame around a rotting reflection",
            style_specific_prefix="decadent etching with watercolor stain",
        )
    if "sherlock" in title_author or "sign of the four" in title_author:
        return BookMotif(
            iconic_scene="detective examining cryptic clues in a gaslit Victorian sitting room",
            character_portrait="razor-focused investigator in long coat and gloves, violin nearby, keen expression",
            setting_landscape="foggy London river docks, hansom cabs, and lamplit alleys",
            dramatic_moment="river pursuit at night as criminals flee through smoke and engine spray",
            symbolic_theme="reason cutting through chaos represented by a magnifying lens over tangled footprints",
            style_specific_prefix="detective copperplate engraving",
        )
    if "les miserables" in title_author:
        return BookMotif(
            iconic_scene="revolutionaries manning a Paris barricade as smoke and flags fill dawn streets",
            character_portrait="hunted ex-convict carrying compassion in his eyes, worn coat, protective stance",
            setting_landscape="19th-century Paris lanes, cathedral silhouettes, and barricades of cobblestone",
            dramatic_moment="final stand amid musket fire while civilians flee under storm light",
            symbolic_theme="mercy versus law embodied by a candle glowing beside broken chains",
            style_specific_prefix="epic historical oil-etch blend",
        )
    if "call of the wild" in title_author:
        return BookMotif(
            iconic_scene="sled dog leading a team across frozen wilderness under aurora and blowing snow",
            character_portrait="powerful canine in harness, fierce eyes, frost-coated fur, primal resolve",
            setting_landscape="Yukon river valley, pine forests, mountains, and pale winter sun",
            dramatic_moment="pack challenge at twilight with snow spraying from clashing bodies",
            symbolic_theme="civilization fading into instinct symbolized by pawprints leaving a campfire",
            style_specific_prefix="northern woodcut composition",
        )
    if "we " in f" {title} ":
        return BookMotif(
            iconic_scene="uniform citizens marching through a transparent city beneath surveillance spires",
            character_portrait="state engineer in numbered uniform, conflicted gaze, rigid geometric backdrop",
            setting_landscape="glass avenues, regimented housing blocks, and metallic skies",
            dramatic_moment="forbidden encounter in a wild zone beyond the city wall",
            symbolic_theme="individual desire cracking a perfect geometric grid",
            style_specific_prefix="constructivist allegorical engraving",
        )
    if "around the world in eighty days" in title_author:
        return BookMotif(
            iconic_scene="disciplined traveler boarding a steam train while clocks and maps surround him",
            character_portrait="Victorian gentleman with pocket watch, composed face, weathered luggage",
            setting_landscape="montage of ports, deserts, rail bridges, and ocean steamers at golden hour",
            dramatic_moment="last-minute sprint toward a club doorway as sunset bells ring",
            symbolic_theme="precision and adventure shown by a globe encircled with train smoke",
            style_specific_prefix="travel poster-style engraving",
        )
    # Author/theme fallbacks.
    if "austen" in author:
        return BookMotif(
            iconic_scene="Regency-era social gathering with restrained glances and layered etiquette",
            character_portrait="poised gentlewoman in period dress, composed posture, intelligent eyes",
            setting_landscape="English countryside estate gardens, rolling fields, and elegant manor architecture",
            dramatic_moment="emotionally charged proposal in rain-lit grounds near an illuminated ballroom",
            symbolic_theme="duty and desire represented by paired gloves resting on a sealed letter",
            style_specific_prefix="Regency watercolor etching",
        )
    if "dickens" in author:
        return BookMotif(
            iconic_scene="crowded Victorian street scene with poverty, warmth, and theatrical human contrast",
            character_portrait="earnest figure in worn coat, expressive face, bustling city behind",
            setting_landscape="soot-darkened London rooftops, gas lamps, and narrow alleys",
            dramatic_moment="moral turning point at dawn with church bells and gathering crowd",
            symbolic_theme="compassion symbolized by a lantern glowing in fog and rain",
            style_specific_prefix="Victorian narrative engraving",
        )
    if "mark twain" in author:
        return BookMotif(
            iconic_scene="mischievous adventure on a riverbank with humor and sudden peril",
            character_portrait="quick-witted youth in simple clothes, sly smile, wind-tossed hair",
            setting_landscape="American river town, wooden docks, steamboat smoke, and broad sky",
            dramatic_moment="high-risk escape by raft under moonlit current",
            symbolic_theme="freedom versus convention represented by a drifting hat on the water",
            style_specific_prefix="Americana ink-wash engraving",
        )
    if "jules verne" in author:
        return BookMotif(
            iconic_scene="ambitious expedition confronting technological marvels in hazardous unknown territory",
            character_portrait="determined explorer-scientist with instruments, maps, and windblown coat",
            setting_landscape="dramatic frontier panorama with machinery, cliffs, and atmospheric sky",
            dramatic_moment="mechanical failure during a storm as team members cling to hope",
            symbolic_theme="human curiosity shown as a compass piercing clouds and darkness",
            style_specific_prefix="scientific adventure lithograph",
        )
    if "dostoyev" in author:
        return BookMotif(
            iconic_scene="tormented figure crossing a dim city square burdened by existential guilt",
            character_portrait="intense eyes, gaunt features, worn coat, and clenched hands in cold light",
            setting_landscape="Northern city canals, cramped interiors, and oppressive winter skies",
            dramatic_moment="shattering confession under candlelight amid law, faith, and despair",
            symbolic_theme="split conscience represented by mirrored silhouettes on wet stone",
            style_specific_prefix="psychological monochrome engraving",
        )
    if "shakespeare" in author:
        return BookMotif(
            iconic_scene="stage-like Renaissance confrontation with nobles, swords, and charged gestures",
            character_portrait="dramatic protagonist in period costume, expressive posture, theatrical light",
            setting_landscape="stone courtyards, banners, and moonlit towers framing courtly intrigue",
            dramatic_moment="fatal climax amid crowd and torchlight in a royal chamber",
            symbolic_theme="ambition and fate represented by a crown beside a cracked dagger",
            style_specific_prefix="theatrical chiaroscuro woodcut",
        )

    return BookMotif(
        iconic_scene="pivotal narrative tableau with period costume, emotional tension, and dramatic environmental storytelling",
        character_portrait="central protagonist in historically grounded attire, expressive face, and purposeful posture",
        setting_landscape="key story environment with layered architecture, atmospheric depth, and symbolic objects",
        dramatic_moment="climactic turning point under turbulent light, motion, and heightened emotional stakes",
        symbolic_theme="core themes represented by allegorical objects, contrasting light, and recursive geometry",
        style_specific_prefix="period-inspired mixed-media engraving",
    )


def generate_prompts_for_book(book_entry: dict, templates: dict) -> list[BookPrompt]:
    """Generate 5 variant prompts for one book entry."""
    motif = _motif_for_book(book_entry)
    variants_cfg = templates["variants"]
    style_groups = templates["style_groups"]
    negative_prompt = templates["negative_prompt"]

    variant_plan = [
        (1, "1_iconic_scene_sketch", "scene_description", _limit_words(motif.iconic_scene)),
        (2, "2_character_portrait_sketch", "character_description", _limit_words(motif.character_portrait)),
        (3, "3_setting_landscape_sketch", "setting_description", _limit_words(motif.setting_landscape)),
        (4, "4_dramatic_oil_painting", "moment_description", _limit_words(motif.dramatic_moment)),
        (5, "5_symbolic_alternative", "theme_description", _limit_words(motif.symbolic_theme)),
    ]

    prompts: list[BookPrompt] = []
    for variant_id, variant_key, description_slot, description_text in variant_plan:
        cfg = variants_cfg[variant_key]
        style_group_name = cfg["style_group"]
        style_group = style_groups[style_group_name]
        style_anchors = style_group["style_anchors"]

        format_kwargs = {
            "scene_description": description_text,
            "character_description": description_text,
            "setting_description": description_text,
            "moment_description": description_text,
            "theme_description": description_text,
            "style_anchors": style_anchors,
            "style_specific_prefix": motif.style_specific_prefix,
        }
        format_kwargs[description_slot] = description_text

        prompt = cfg["template"].format(**format_kwargs)
        prompt = _strip_forbidden(prompt, book_entry["title"], book_entry["author"])
        prompt = diversify_prompt(prompt, variant_id)
        prompt = _ensure_prompt_constraints(prompt)

        prompts.append(
            BookPrompt(
                book_number=book_entry["number"],
                book_title=book_entry["title"],
                book_author=book_entry["author"],
                variant_id=variant_id,
                variant_key=variant_key,
                variant_name=cfg["name"],
                description=description_text,
                prompt=prompt,
                negative_prompt=negative_prompt,
                style_reference=style_group_name,
            )
        )

    return prompts


def generate_all_prompts(catalog_path: Path, templates_path: Path) -> list[dict[str, Any]]:
    """Generate all prompt records for the full catalog."""
    catalog = safe_json.load_json(catalog_path, [])
    templates = safe_json.load_json(templates_path, {})

    all_records: list[dict[str, Any]] = []
    for book in catalog if isinstance(catalog, list) else []:
        if not isinstance(book, dict):
            continue
        variant_prompts = generate_prompts_for_book(book, templates)
        record = {
            "number": book["number"],
            "title": book["title"],
            "author": book["author"],
            "folder_name": book.get("folder_name"),
            "file_base": book.get("file_base"),
            "variants": [item.to_dict() for item in variant_prompts],
        }
        all_records.append(record)
    return all_records


def save_prompts(prompts: list[dict[str, Any]], output_path: Path) -> None:
    """Save generated prompts as JSON."""
    payload = {
        "book_count": len(prompts),
        "variant_count_per_book": 5,
        "total_prompts": len(prompts) * 5,
        "books": prompts,
    }
    safe_json.atomic_write_json(output_path, payload)
    logger.info("Wrote %d prompts for %d books to %s", len(prompts) * 5, len(prompts), output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Prompt 1B prompt catalog.")
    parser.add_argument("--catalog-path", type=Path, default=DEFAULT_CATALOG_PATH)
    parser.add_argument("--templates-path", type=Path, default=DEFAULT_TEMPLATES_PATH)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()

    prompts = generate_all_prompts(args.catalog_path, args.templates_path)
    save_prompts(prompts, args.output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
