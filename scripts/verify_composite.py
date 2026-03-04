#!/usr/bin/env python3
"""
Visual Regression Test for Alexandria Cover Designer Compositing.

Compares a composited cover output against its source cover JPG to verify:
1. ORNAMENT ZONE (r > 480px from center): Frame pixels are IDENTICAL to source
2. ART ZONE (r < 370px from center): Pixels DIFFER from source (AI art replaced them)
3. TRANSITION ZONE (370-480px): Smooth blending, no hard edges
4. CENTERING: Art center coincides with medallion center (2864, 1620)

Usage:
    python scripts/verify_composite.py <composited.jpg> <source_cover.jpg>
    python scripts/verify_composite.py <composited.jpg> <source_cover.jpg> --strict
    python scripts/verify_composite.py --batch <output_dir> <source_covers_dir>

Exit codes:
    0 = ALL CHECKS PASSED
    1 = ONE OR MORE CHECKS FAILED
    2 = ERROR (missing files, wrong dimensions, etc.)

This script MUST be run after every compositor change before committing.
Both Claude Cowork and Codex are required to run this and report results.
"""

import argparse
import sys
import json
from pathlib import Path

import numpy as np
from PIL import Image

# ── Known Geometry ──
CENTER_X = 2864
CENTER_Y = 1620
OUTER_FRAME_RADIUS = 500

# ── Test Zone Radii ──
ORNAMENT_ZONE_MIN = 480   # Beyond this = pure frame, must match source
ART_ZONE_MAX = 370        # Inside this = pure art, must differ from source
# Between 370-480 = transition zone (scrollwork + art boundary)

# ── Thresholds ──
ORNAMENT_MATCH_THRESHOLD = 0.995   # 99.5% of ornament pixels must be identical
ART_DIFFER_THRESHOLD = 0.90        # 90% of art zone pixels must differ from source
CHANNEL_DIFF_TOLERANCE = 2         # JPEG compression tolerance (0-255 scale)
CENTERING_TOLERANCE_PX = 5         # Art center must be within 5px of medallion center


def load_image_array(path: Path) -> np.ndarray:
    """Load image as RGB numpy array."""
    img = Image.open(path).convert("RGB")
    return np.array(img, dtype=np.uint8)


def make_radial_mask(shape: tuple, center_x: int, center_y: int, radius: float) -> np.ndarray:
    """Create a boolean mask for pixels within radius of center."""
    h, w = shape[:2]
    yy, xx = np.ogrid[:h, :w]
    dist_sq = (xx - center_x).astype(np.float64)**2 + (yy - center_y).astype(np.float64)**2
    return dist_sq <= radius**2


def check_ornament_zone(composite: np.ndarray, source: np.ndarray) -> dict:
    """Check that ornament zone pixels match the source cover exactly."""
    # Ornament zone: outside ORNAMENT_ZONE_MIN radius but inside image
    ornament_mask = ~make_radial_mask(composite.shape, CENTER_X, CENTER_Y, ORNAMENT_ZONE_MIN)

    # Also exclude pixels outside the outer frame (pure background, may differ)
    frame_outer = make_radial_mask(composite.shape, CENTER_X, CENTER_Y, OUTER_FRAME_RADIUS + 50)
    ornament_mask = ornament_mask & frame_outer

    # But we also want to check the rest of the cover OUTSIDE the medallion area entirely
    # The entire cover outside the medallion region should be identical
    full_cover_mask = ~make_radial_mask(composite.shape, CENTER_X, CENTER_Y, OUTER_FRAME_RADIUS + 50)

    # Combine: check ornament ring + everything outside medallion
    check_mask = ornament_mask | full_cover_mask

    total_pixels = int(np.sum(check_mask))
    if total_pixels == 0:
        return {"pass": False, "error": "No ornament zone pixels found"}

    # Per-pixel max channel difference
    diff = np.max(np.abs(composite.astype(np.int16) - source.astype(np.int16)), axis=2)
    matching = np.sum((diff[check_mask] <= CHANNEL_DIFF_TOLERANCE))
    match_ratio = float(matching) / total_pixels

    passed = match_ratio >= ORNAMENT_MATCH_THRESHOLD
    return {
        "pass": passed,
        "match_ratio": round(match_ratio, 6),
        "threshold": ORNAMENT_MATCH_THRESHOLD,
        "total_pixels": total_pixels,
        "matching_pixels": int(matching),
        "mismatched_pixels": total_pixels - int(matching),
        "message": (
            f"PASS: {match_ratio:.2%} of frame/ornament pixels match source"
            if passed else
            f"FAIL: Only {match_ratio:.2%} of frame/ornament pixels match source "
            f"(need {ORNAMENT_MATCH_THRESHOLD:.1%}). {total_pixels - int(matching):,} pixels differ."
        ),
    }


def check_art_zone(composite: np.ndarray, source: np.ndarray) -> dict:
    """Check that art zone pixels differ from source (AI art replaced them)."""
    art_mask = make_radial_mask(composite.shape, CENTER_X, CENTER_Y, ART_ZONE_MAX)

    total_pixels = int(np.sum(art_mask))
    if total_pixels == 0:
        return {"pass": False, "error": "No art zone pixels found"}

    # Per-pixel max channel difference
    diff = np.max(np.abs(composite.astype(np.int16) - source.astype(np.int16)), axis=2)
    different = np.sum(diff[art_mask] > CHANNEL_DIFF_TOLERANCE)
    differ_ratio = float(different) / total_pixels

    passed = differ_ratio >= ART_DIFFER_THRESHOLD
    return {
        "pass": passed,
        "differ_ratio": round(differ_ratio, 6),
        "threshold": ART_DIFFER_THRESHOLD,
        "total_pixels": total_pixels,
        "different_pixels": int(different),
        "same_pixels": total_pixels - int(different),
        "message": (
            f"PASS: {differ_ratio:.2%} of art zone pixels differ from source (AI art present)"
            if passed else
            f"FAIL: Only {differ_ratio:.2%} of art zone pixels differ from source "
            f"(need {ART_DIFFER_THRESHOLD:.0%}). Original cover art may still be visible."
        ),
    }


def check_centering(composite: np.ndarray, source: np.ndarray) -> dict:
    """Check that the AI art is centered at the medallion center."""
    # Strategy: find the bounding box of pixels that differ significantly
    diff = np.max(np.abs(composite.astype(np.int16) - source.astype(np.int16)), axis=2)
    art_pixels = diff > 20  # Significant difference = art pixel

    # Only look within the medallion area
    medallion_mask = make_radial_mask(composite.shape, CENTER_X, CENTER_Y, OUTER_FRAME_RADIUS)
    art_in_medallion = art_pixels & medallion_mask

    if not np.any(art_in_medallion):
        return {"pass": False, "error": "No art detected in medallion area"}

    # Find center of mass of art pixels
    ys, xs = np.where(art_in_medallion)
    art_center_x = float(np.mean(xs))
    art_center_y = float(np.mean(ys))

    offset_x = abs(art_center_x - CENTER_X)
    offset_y = abs(art_center_y - CENTER_Y)
    offset_total = (offset_x**2 + offset_y**2)**0.5

    passed = offset_total <= CENTERING_TOLERANCE_PX
    return {
        "pass": passed,
        "art_center_x": round(art_center_x, 1),
        "art_center_y": round(art_center_y, 1),
        "expected_center_x": CENTER_X,
        "expected_center_y": CENTER_Y,
        "offset_x": round(offset_x, 1),
        "offset_y": round(offset_y, 1),
        "offset_total": round(offset_total, 1),
        "tolerance": CENTERING_TOLERANCE_PX,
        "message": (
            f"PASS: Art centered at ({art_center_x:.0f}, {art_center_y:.0f}), "
            f"offset {offset_total:.1f}px from medallion center"
            if passed else
            f"FAIL: Art centered at ({art_center_x:.0f}, {art_center_y:.0f}), "
            f"offset {offset_total:.1f}px exceeds {CENTERING_TOLERANCE_PX}px tolerance"
        ),
    }


def check_dimensions(composite: np.ndarray, source: np.ndarray) -> dict:
    """Check output dimensions match source."""
    comp_h, comp_w = composite.shape[:2]
    src_h, src_w = source.shape[:2]

    dims_match = (comp_w == src_w) and (comp_h == src_h)
    expected = (comp_w == 3784 and comp_h == 2777)

    passed = dims_match and expected
    return {
        "pass": passed,
        "composite_size": f"{comp_w}x{comp_h}",
        "source_size": f"{src_w}x{src_h}",
        "expected_size": "3784x2777",
        "message": (
            f"PASS: Dimensions {comp_w}x{comp_h} match source and expected size"
            if passed else
            f"FAIL: Composite={comp_w}x{comp_h}, Source={src_w}x{src_h}, Expected=3784x2777"
        ),
    }


def check_transition_zone(composite: np.ndarray, source: np.ndarray) -> dict:
    """Check the transition zone for quality (no harsh artifacts)."""
    # Transition zone: between ART_ZONE_MAX and ORNAMENT_ZONE_MIN
    inner = make_radial_mask(composite.shape, CENTER_X, CENTER_Y, ART_ZONE_MAX)
    outer = make_radial_mask(composite.shape, CENTER_X, CENTER_Y, ORNAMENT_ZONE_MIN)
    transition_mask = outer & ~inner

    total_pixels = int(np.sum(transition_mask))
    if total_pixels == 0:
        return {"pass": False, "error": "No transition zone pixels found"}

    # Check for harsh color discontinuities (gradient magnitude)
    # High gradient = potential artifact
    comp_gray = np.mean(composite.astype(np.float32), axis=2)

    # Sobel-like gradient (simple difference)
    grad_x = np.abs(np.diff(comp_gray, axis=1, prepend=comp_gray[:, :1]))
    grad_y = np.abs(np.diff(comp_gray, axis=0, prepend=comp_gray[:1, :]))
    gradient = np.sqrt(grad_x**2 + grad_y**2)

    # In transition zone, check for extreme gradients (artifacts)
    transition_gradient = gradient[transition_mask]
    harsh_pixels = np.sum(transition_gradient > 100)  # Very harsh edge
    harsh_ratio = float(harsh_pixels) / total_pixels

    passed = harsh_ratio < 0.02  # Less than 2% harsh pixels
    return {
        "pass": passed,
        "harsh_pixel_ratio": round(harsh_ratio, 6),
        "max_gradient": float(np.max(transition_gradient)),
        "mean_gradient": round(float(np.mean(transition_gradient)), 2),
        "total_pixels": total_pixels,
        "message": (
            f"PASS: Transition zone clean ({harsh_ratio:.2%} harsh pixels)"
            if passed else
            f"FAIL: Transition zone has artifacts ({harsh_ratio:.2%} harsh pixels, "
            f"max gradient={np.max(transition_gradient):.0f})"
        ),
    }


def verify_composite(composite_path: Path, source_path: Path, strict: bool = False) -> dict:
    """Run all verification checks on a composited cover."""
    print(f"\n{'='*70}")
    print(f"COMPOSITE VERIFICATION")
    print(f"  Composite: {composite_path.name}")
    print(f"  Source:    {source_path.name}")
    print(f"{'='*70}\n")

    try:
        composite = load_image_array(composite_path)
        source = load_image_array(source_path)
    except Exception as e:
        print(f"ERROR: Failed to load images: {e}")
        return {"overall_pass": False, "error": str(e)}

    checks = {
        "dimensions": check_dimensions(composite, source),
        "ornament_zone": check_ornament_zone(composite, source),
        "art_zone": check_art_zone(composite, source),
        "centering": check_centering(composite, source),
        "transition_quality": check_transition_zone(composite, source),
    }

    all_passed = all(c["pass"] for c in checks.values())

    for name, result in checks.items():
        status = "PASS" if result["pass"] else "FAIL"
        icon = "+" if result["pass"] else "X"
        print(f"  [{icon}] {name}: {result.get('message', status)}")

    print(f"\n{'='*70}")
    if all_passed:
        print("  RESULT: ALL CHECKS PASSED")
    else:
        failed = [k for k, v in checks.items() if not v["pass"]]
        print(f"  RESULT: FAILED ({len(failed)} check(s): {', '.join(failed)})")
    print(f"{'='*70}\n")

    return {
        "overall_pass": all_passed,
        "checks": checks,
        "composite_path": str(composite_path),
        "source_path": str(source_path),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Verify composited cover output against source cover."
    )
    parser.add_argument("composite", type=Path, help="Path to composited output JPG")
    parser.add_argument("source", type=Path, help="Path to source cover JPG")
    parser.add_argument("--strict", action="store_true", help="Stricter thresholds")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    if not args.composite.exists():
        print(f"ERROR: Composite file not found: {args.composite}", file=sys.stderr)
        sys.exit(2)
    if not args.source.exists():
        print(f"ERROR: Source file not found: {args.source}", file=sys.stderr)
        sys.exit(2)

    if args.strict:
        global ORNAMENT_MATCH_THRESHOLD, ART_DIFFER_THRESHOLD, CENTERING_TOLERANCE_PX
        ORNAMENT_MATCH_THRESHOLD = 0.999
        ART_DIFFER_THRESHOLD = 0.95
        CENTERING_TOLERANCE_PX = 3

    result = verify_composite(args.composite, args.source)

    if args.json:
        # Sanitize for JSON serialization
        def sanitize(obj):
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj

        clean = json.loads(json.dumps(result, default=sanitize))
        print(json.dumps(clean, indent=2))

    sys.exit(0 if result["overall_pass"] else 1)


if __name__ == "__main__":
    main()
