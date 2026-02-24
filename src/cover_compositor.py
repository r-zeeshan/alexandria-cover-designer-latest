"""Prompt 3A cover compositing for circle/rectangle/custom regions."""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

try:
    from src import config
    from src import safe_json
    from src.logger import get_logger
except ModuleNotFoundError:  # pragma: no cover
    import config  # type: ignore
    import safe_json  # type: ignore
    from logger import get_logger  # type: ignore

logger = get_logger(__name__)


@dataclass(slots=True)
class Region:
    center_x: int
    center_y: int
    radius: int
    frame_bbox: tuple[int, int, int, int]
    region_type: str = "circle"
    rect_bbox: tuple[int, int, int, int] | None = None
    mask_path: str | None = None


@dataclass(slots=True)
class CompositeValidation:
    output_path: str
    valid: bool
    issues: list[str]
    dimensions_ok: bool
    dpi_ok: bool
    file_size_ok: bool
    alignment_ok: bool
    border_bleed_ok: bool
    edge_artifacts_ok: bool
    metrics: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_path": self.output_path,
            "valid": self.valid,
            "issues": list(self.issues),
            "dimensions_ok": self.dimensions_ok,
            "dpi_ok": self.dpi_ok,
            "file_size_ok": self.file_size_ok,
            "alignment_ok": self.alignment_ok,
            "border_bleed_ok": self.border_bleed_ok,
            "edge_artifacts_ok": self.edge_artifacts_ok,
            "metrics": dict(self.metrics),
        }


def composite_single(
    cover_path: Path,
    illustration_path: Path,
    region: dict[str, Any],
    output_path: Path,
    feather_px: int = 15,
    frame_overlap_px: int = 18,
) -> Path:
    """Composite one illustration into a cover image."""
    runtime = config.get_config()
    cover = Image.open(cover_path).convert("RGB")
    illustration = Image.open(illustration_path).convert("RGBA")
    illustration = _strip_border(illustration, border_percent=float(getattr(runtime, "border_strip_percent", 0.05)))

    if cover.size != (3784, 2777):
        logger.warning("Cover %s has unexpected size %s", cover_path, cover.size)

    region_obj = _region_from_dict(region)
    cover_w, cover_h = cover.size

    full_overlay = Image.new("RGBA", (cover_w, cover_h), (0, 0, 0, 0))

    if region_obj.region_type == "rectangle" and region_obj.rect_bbox is not None:
        x1, y1, x2, y2 = region_obj.rect_bbox
        target_w = max(1, x2 - x1)
        target_h = max(1, y2 - y1)
        resized = illustration.resize((target_w, target_h), Image.LANCZOS)
        resized = _color_match_illustration(cover=cover, illustration=resized, region=region_obj)
        full_overlay.paste(resized, (x1, y1))

        mask = _build_rect_feather_mask(
            width=cover_w,
            height=cover_h,
            bbox=(x1, y1, x2, y2),
            feather_px=feather_px,
        )
    elif region_obj.region_type == "custom_mask" and region_obj.mask_path:
        effective_radius = max(20, region_obj.radius - frame_overlap_px)
        diameter = effective_radius * 2
        resized = illustration.resize((diameter, diameter), Image.LANCZOS)
        resized = _color_match_illustration(cover=cover, illustration=resized, region=region_obj)
        _paste_centered(
            canvas=full_overlay,
            overlay=resized,
            center_x=region_obj.center_x,
            center_y=region_obj.center_y,
        )

        mask = _load_custom_mask(region_obj.mask_path, cover.size)
    else:
        effective_radius = max(20, region_obj.radius - frame_overlap_px)
        diameter = effective_radius * 2

        resized = illustration.resize((diameter, diameter), Image.LANCZOS)
        resized = _color_match_illustration(cover=cover, illustration=resized, region=region_obj)

        _paste_centered(
            canvas=full_overlay,
            overlay=resized,
            center_x=region_obj.center_x,
            center_y=region_obj.center_y,
        )

        mask = _build_circle_feather_mask(
            width=cover_w,
            height=cover_h,
            center_x=region_obj.center_x,
            center_y=region_obj.center_y,
            radius=effective_radius,
            feather_px=feather_px,
        )

    full_overlay.putalpha(mask)

    composited_rgba = Image.alpha_composite(cover.convert("RGBA"), full_overlay)
    composited_rgb = composited_rgba.convert("RGB")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    composited_rgb.save(output_path, format="JPEG", quality=100, subsampling=0, dpi=(300, 300))
    validation = validate_composite_output(
        cover=cover,
        composited=composited_rgb,
        region=region_obj,
        output_path=output_path,
    )
    safe_json.atomic_write_json(
        _validation_path(output_path),
        {
            **validation.to_dict(),
            "validated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    if not validation.valid:
        logger.warning("Composite validation issues for %s: %s", output_path, ", ".join(validation.issues))
    return output_path


def generate_fit_overlay(cover_path: Path, region: dict[str, Any], output_path: Path) -> Path:
    """Generate visual overlay for fit verification in review UI."""
    base = Image.open(cover_path).convert("RGBA")
    draw = ImageDraw.Draw(base, "RGBA")
    reg = _region_from_dict(region)

    if reg.region_type == "rectangle" and reg.rect_bbox is not None:
        x1, y1, x2, y2 = reg.rect_bbox
        draw.rectangle((x1, y1, x2, y2), outline=(255, 64, 64, 230), width=6, fill=(255, 64, 64, 40))
    else:
        comp_radius = max(20, reg.radius - 18)
        draw.ellipse(
            (
                reg.center_x - comp_radius,
                reg.center_y - comp_radius,
                reg.center_x + comp_radius,
                reg.center_y + comp_radius,
            ),
            outline=(255, 64, 64, 230),
            width=6,
            fill=(255, 64, 64, 40),
        )
        draw.ellipse(
            (
                reg.center_x - reg.radius,
                reg.center_y - reg.radius,
                reg.center_x + reg.radius,
                reg.center_y + reg.radius,
            ),
            outline=(255, 210, 90, 230),
            width=4,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path, format="PNG")
    return output_path


def composite_all_variants(
    book_number: int,
    input_dir: Path,
    generated_dir: Path,
    output_dir: Path,
    regions: dict[str, Any],
    *,
    catalog_path: Path = config.BOOK_CATALOG_PATH,
) -> list[Path]:
    """Composite all available generated variants for one book."""
    cover_path = _find_cover_jpg(input_dir, book_number, catalog_path=catalog_path)
    region = _region_for_book(regions, book_number)

    image_rows = _collect_generated_for_book(generated_dir, book_number)
    if not image_rows:
        raise FileNotFoundError(f"No generated images found for book {book_number} in {generated_dir}")

    outputs: list[Path] = []
    validations: list[dict[str, Any]] = []
    for row in image_rows:
        if row["model"] == "default":
            out_path = output_dir / str(book_number) / f"variant_{row['variant']}.jpg"
        else:
            out_path = output_dir / str(book_number) / row["model"] / f"variant_{row['variant']}.jpg"

        composite_single(
            cover_path=cover_path,
            illustration_path=row["path"],
            region=region,
            output_path=out_path,
        )
        outputs.append(out_path)
        validation_payload = _load_validation_payload(out_path)
        if validation_payload:
            validations.append(validation_payload)

    generate_fit_overlay(
        cover_path=cover_path,
        region=region,
        output_path=output_dir / str(book_number) / "fit_overlay.png",
    )

    if validations:
        summary = {
            "book_number": int(book_number),
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "total": len(validations),
            "invalid": sum(1 for row in validations if not bool(row.get("valid", False))),
            "items": validations,
        }
        report_path = output_dir / str(book_number) / "composite_validation.json"
        safe_json.atomic_write_json(report_path, summary)

    return outputs


def validate_composite_output(
    *,
    cover: Image.Image,
    composited: Image.Image,
    region: Region,
    output_path: Path,
) -> CompositeValidation:
    issues: list[str] = []
    cover_arr = np.array(cover.convert("RGB"), dtype=np.int16)
    comp_arr = np.array(composited.convert("RGB"), dtype=np.int16)
    diff = np.abs(comp_arr - cover_arr).mean(axis=2)
    changed = diff > 6.0

    dimensions_ok = tuple(composited.size) == tuple(cover.size)
    if not dimensions_ok:
        issues.append("dimension_mismatch")

    try:
        with Image.open(output_path) as output_meta:
            dpi = output_meta.info.get("dpi", (0, 0))
    except Exception:  # pragma: no cover - defensive
        dpi = (0, 0)
    dpi_x, dpi_y = (float(dpi[0]) if len(dpi) > 0 else 0.0, float(dpi[1]) if len(dpi) > 1 else 0.0)
    dpi_ok = dpi_x >= 295.0 and dpi_y >= 295.0
    if not dpi_ok:
        issues.append("dpi_metadata_invalid")

    file_size_kb = float(output_path.stat().st_size) / 1024.0 if output_path.exists() else 0.0
    file_size_ok = 60.0 <= file_size_kb <= 30_000.0
    if not file_size_ok:
        issues.append("file_size_out_of_bounds")

    h, w = diff.shape
    if np.any(changed):
        changed_points = np.argwhere(changed)
        centroid_y = float(changed_points[:, 0].mean())
        centroid_x = float(changed_points[:, 1].mean())
    else:
        centroid_x = float(region.center_x)
        centroid_y = float(region.center_y)
        issues.append("no_visible_composite_difference")

    if region.region_type == "rectangle" and region.rect_bbox is not None:
        x1, y1, x2, y2 = region.rect_bbox
        target_x = (x1 + x2) / 2.0
        target_y = (y1 + y2) / 2.0
        tolerance = max(25.0, max(x2 - x1, y2 - y1) * 0.40)
        expected_mask = np.zeros((h, w), dtype=bool)
        expected_mask[max(0, y1 - 10):min(h, y2 + 10), max(0, x1 - 10):min(w, x2 + 10)] = True
    else:
        target_x = float(region.center_x)
        target_y = float(region.center_y)
        tolerance = max(25.0, float(region.radius) * 0.45)
        yy, xx = np.ogrid[:h, :w]
        dist = np.sqrt((xx - target_x) ** 2 + (yy - target_y) ** 2)
        expected_mask = dist <= max(10.0, float(region.radius) + 10.0)

    alignment_distance = float(np.sqrt((centroid_x - target_x) ** 2 + (centroid_y - target_y) ** 2))
    alignment_ok = alignment_distance <= tolerance
    if not alignment_ok:
        issues.append("alignment_offset_high")

    outside_expected = ~expected_mask
    bleed_ratio = float(changed[outside_expected].mean()) if outside_expected.any() else 0.0
    border_bleed_ok = bleed_ratio <= 0.02
    if not border_bleed_ok:
        issues.append("border_bleed_detected")

    ring_strength = 0.0
    if region.region_type != "rectangle":
        yy, xx = np.ogrid[:h, :w]
        dist = np.sqrt((xx - target_x) ** 2 + (yy - target_y) ** 2)
        ring = (dist >= max(0.0, float(region.radius) - 6.0)) & (dist <= float(region.radius) + 6.0)
        if ring.any():
            ring_strength = float(np.percentile(diff[ring], 95))
    edge_artifacts_ok = ring_strength <= 130.0
    if not edge_artifacts_ok:
        issues.append("edge_artifact_risk")

    return CompositeValidation(
        output_path=str(output_path),
        valid=bool(dimensions_ok and dpi_ok and file_size_ok and alignment_ok and border_bleed_ok and edge_artifacts_ok),
        issues=issues,
        dimensions_ok=bool(dimensions_ok),
        dpi_ok=bool(dpi_ok),
        file_size_ok=bool(file_size_ok),
        alignment_ok=bool(alignment_ok),
        border_bleed_ok=bool(border_bleed_ok),
        edge_artifacts_ok=bool(edge_artifacts_ok),
        metrics={
            "dpi_x": round(dpi_x, 3),
            "dpi_y": round(dpi_y, 3),
            "file_size_kb": round(file_size_kb, 3),
            "alignment_distance_px": round(alignment_distance, 3),
            "alignment_tolerance_px": round(float(tolerance), 3),
            "border_bleed_ratio": round(bleed_ratio, 6),
            "edge_ring_strength": round(ring_strength, 3),
        },
    )


def batch_composite(
    input_dir: Path,
    generated_dir: Path,
    output_dir: Path,
    regions_path: Path,
    *,
    book_numbers: list[int] | None = None,
    max_books: int = 20,
    catalog_path: Path = config.BOOK_CATALOG_PATH,
) -> dict[str, Any]:
    """Composite all generated books with error isolation."""
    regions = safe_json.load_json(regions_path, {})
    generated_books = sorted(
        [int(path.name) for path in generated_dir.iterdir() if path.is_dir() and path.name.isdigit()]
    )

    if book_numbers:
        target_books = [b for b in generated_books if b in set(book_numbers)]
    else:
        target_books = generated_books[:max_books]

    summary = {
        "processed_books": 0,
        "success_books": 0,
        "failed_books": 0,
        "outputs": 0,
        "errors": [],
    }

    for book_number in target_books:
        summary["processed_books"] += 1
        try:
            outputs = composite_all_variants(
                book_number=book_number,
                input_dir=input_dir,
                generated_dir=generated_dir,
                output_dir=output_dir,
                regions=regions,
                catalog_path=catalog_path,
            )
            summary["success_books"] += 1
            summary["outputs"] += len(outputs)
        except Exception as exc:  # pragma: no cover - defensive
            summary["failed_books"] += 1
            summary["errors"].append({"book_number": book_number, "error": str(exc)})
            logger.error("Compositing failed for book %s: %s", book_number, exc)

    return summary


def _region_from_dict(region: dict[str, Any]) -> Region:
    bbox = region.get("frame_bbox", [0, 0, 0, 0])
    rect = region.get("rect_bbox")
    rect_bbox = None
    if isinstance(rect, list) and len(rect) == 4:
        rect_bbox = (int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3]))

    return Region(
        center_x=int(region.get("center_x", 0)),
        center_y=int(region.get("center_y", 0)),
        radius=int(region.get("radius", 0)),
        frame_bbox=(int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])),
        region_type=str(region.get("region_type", "circle") or "circle"),
        rect_bbox=rect_bbox,
        mask_path=str(region.get("mask_path", "") or "") or None,
    )


def _strip_border(image: Image.Image, border_percent: float = 0.05) -> Image.Image:
    """Crop a symmetric outer strip to remove AI-added frame/border artifacts."""
    percent = max(0.0, min(0.20, float(border_percent or 0.0)))
    if percent <= 0:
        return image
    width, height = image.size
    crop_x = int(width * percent)
    crop_y = int(height * percent)
    if crop_x <= 0 and crop_y <= 0:
        return image
    left = max(0, crop_x)
    top = max(0, crop_y)
    right = min(width, width - crop_x)
    bottom = min(height, height - crop_y)
    if right <= left or bottom <= top:
        return image
    cropped = image.crop((left, top, right, bottom))
    return cropped


def _paste_centered(*, canvas: Image.Image, overlay: Image.Image, center_x: int, center_y: int) -> None:
    """Paste overlay so its center aligns exactly to the requested coordinates."""
    paste_x = int(center_x) - int(overlay.width // 2)
    paste_y = int(center_y) - int(overlay.height // 2)
    if overlay.mode == "RGBA":
        canvas.paste(overlay, (paste_x, paste_y), overlay)
    else:
        canvas.paste(overlay, (paste_x, paste_y))


def _build_circle_feather_mask(
    *,
    width: int,
    height: int,
    center_x: int,
    center_y: int,
    radius: int,
    feather_px: int,
) -> Image.Image:
    yy, xx = np.ogrid[:height, :width]
    dist = np.sqrt((xx - center_x) ** 2 + (yy - center_y) ** 2)

    alpha = np.zeros((height, width), dtype=np.float32)
    inner = radius - feather_px
    alpha[dist <= inner] = 255.0

    feather_zone = (dist > inner) & (dist <= radius)
    alpha[feather_zone] = np.clip((radius - dist[feather_zone]) / max(1, feather_px) * 255.0, 0, 255)
    return Image.fromarray(alpha.astype(np.uint8), mode="L")


def _build_rect_feather_mask(*, width: int, height: int, bbox: tuple[int, int, int, int], feather_px: int) -> Image.Image:
    x1, y1, x2, y2 = bbox
    alpha = np.zeros((height, width), dtype=np.float32)
    alpha[y1:y2, x1:x2] = 255.0

    # Soft edge feather.
    for step in range(1, max(1, feather_px) + 1):
        value = max(0.0, 255.0 * (1.0 - (step / max(1, feather_px))))
        alpha[max(0, y1 - step):y1, max(0, x1 - step):min(width, x2 + step)] = np.maximum(
            alpha[max(0, y1 - step):y1, max(0, x1 - step):min(width, x2 + step)], value
        )
        alpha[y2:min(height, y2 + step), max(0, x1 - step):min(width, x2 + step)] = np.maximum(
            alpha[y2:min(height, y2 + step), max(0, x1 - step):min(width, x2 + step)], value
        )
        alpha[max(0, y1 - step):min(height, y2 + step), max(0, x1 - step):x1] = np.maximum(
            alpha[max(0, y1 - step):min(height, y2 + step), max(0, x1 - step):x1], value
        )
        alpha[max(0, y1 - step):min(height, y2 + step), x2:min(width, x2 + step)] = np.maximum(
            alpha[max(0, y1 - step):min(height, y2 + step), x2:min(width, x2 + step)], value
        )

    return Image.fromarray(np.clip(alpha, 0, 255).astype(np.uint8), mode="L")


def _load_custom_mask(mask_path: str, size: tuple[int, int]) -> Image.Image:
    candidate = Path(mask_path)
    if not candidate.is_absolute():
        candidate = config.PROJECT_ROOT / candidate
    if not candidate.exists():
        logger.warning("Custom mask path missing: %s", candidate)
        return Image.new("L", size, 255)

    mask = Image.open(candidate).convert("L")
    if mask.size != size:
        mask = mask.resize(size, Image.LANCZOS)
    return mask


def _validation_path(output_path: Path) -> Path:
    return output_path.with_suffix(output_path.suffix + ".validation.json")


def _load_validation_payload(output_path: Path) -> dict[str, Any] | None:
    path = _validation_path(output_path)
    payload = safe_json.load_json(path, None)
    if not isinstance(payload, dict):
        return None
    return payload


def _color_match_illustration(cover: Image.Image, illustration: Image.Image, region: Region) -> Image.Image:
    """Nudge illustration color temperature toward region context."""
    cover_arr = np.array(cover.convert("RGB"), dtype=np.float32)
    ill_arr = np.array(illustration.convert("RGB"), dtype=np.float32)

    yy, xx = np.ogrid[:cover_arr.shape[0], :cover_arr.shape[1]]
    if region.region_type == "rectangle" and region.rect_bbox is not None:
        x1, y1, x2, y2 = region.rect_bbox
        ring = np.zeros((cover_arr.shape[0], cover_arr.shape[1]), dtype=bool)
        ring[max(0, y1 - 30):min(cover_arr.shape[0], y2 + 30), max(0, x1 - 30):min(cover_arr.shape[1], x2 + 30)] = True
        ring[y1:y2, x1:x2] = False
    else:
        dist = np.sqrt((xx - region.center_x) ** 2 + (yy - region.center_y) ** 2)
        ring = (dist >= region.radius - 60) & (dist <= region.radius - 10)

    if not np.any(ring):
        return illustration

    target_mean = cover_arr[ring].mean(axis=0)
    ill_mean = ill_arr.reshape(-1, 3).mean(axis=0)

    scale = np.clip((target_mean + 1.0) / (ill_mean + 1.0), 0.78, 1.22)
    matched = np.clip(ill_arr * scale, 0, 255).astype(np.uint8)

    alpha = np.array(illustration)[..., 3:4] if illustration.mode == "RGBA" else np.full((*matched.shape[:2], 1), 255, dtype=np.uint8)
    rgba = np.concatenate([matched, alpha], axis=2)
    return Image.fromarray(rgba, mode="RGBA")


def _load_catalog(path: Path) -> list[dict[str, Any]]:
    payload = safe_json.load_json(path, [])
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def _find_cover_jpg(input_dir: Path, book_number: int, *, catalog_path: Path) -> Path:
    catalog = _load_catalog(catalog_path)
    match = None
    for entry in catalog:
        if int(entry.get("number", 0)) == int(book_number):
            match = entry
            break
    if not match:
        raise KeyError(f"Book {book_number} not found in catalog")

    folder = input_dir / str(match["folder_name"])
    if not folder.exists():
        raise FileNotFoundError(f"Cover folder missing: {folder}")

    jpg_candidates = sorted(folder.glob("*.jpg"))
    if not jpg_candidates:
        raise FileNotFoundError(f"No JPG found in {folder}")
    return jpg_candidates[0]


def _region_for_book(regions_payload: dict[str, Any], book_number: int) -> dict[str, Any]:
    for row in regions_payload.get("covers", []):
        if int(row.get("cover_id", 0)) == int(book_number):
            return row
    return regions_payload.get("consensus_region", {})


def _collect_generated_for_book(generated_dir: Path, book_number: int) -> list[dict[str, Any]]:
    base = generated_dir / str(book_number)
    if not base.exists():
        return []

    rows: list[dict[str, Any]] = []

    for model_dir in sorted([path for path in base.iterdir() if path.is_dir()]):
        if model_dir.name == "history":
            continue
        for image in sorted(model_dir.glob("variant_*.png")):
            variant = _parse_variant(image.stem)
            rows.append({"model": model_dir.name, "variant": variant, "path": image})

    for image in sorted(base.glob("variant_*.png")):
        variant = _parse_variant(image.stem)
        rows.append({"model": "default", "variant": variant, "path": image})

    dedup: dict[tuple[str, int], dict[str, Any]] = {}
    for row in rows:
        dedup[(row["model"], row["variant"])] = row

    return sorted(dedup.values(), key=lambda row: (row["model"], row["variant"]))


def _parse_variant(stem: str) -> int:
    if "variant_" not in stem:
        return 0
    token = stem.split("variant_", 1)[1].split("_", 1)[0]
    try:
        return int(token)
    except ValueError:
        return 0


def _parse_books(raw: str | None) -> list[int] | None:
    if not raw:
        return None

    books: set[int] = set()
    for piece in raw.split(","):
        token = piece.strip()
        if not token:
            continue
        if "-" in token:
            start_str, end_str = token.split("-", 1)
            start, end = int(start_str), int(end_str)
            for value in range(min(start, end), max(start, end) + 1):
                books.add(value)
        else:
            books.add(int(token))

    return sorted(books)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prompt 3A cover compositing")
    parser.add_argument("--input-dir", type=Path, default=config.INPUT_DIR)
    parser.add_argument("--generated-dir", type=Path, default=config.TMP_DIR / "generated")
    parser.add_argument("--output-dir", type=Path, default=config.TMP_DIR / "composited")
    parser.add_argument("--regions-path", type=Path, default=config.CONFIG_DIR / "cover_regions.json")
    parser.add_argument("--catalog-path", type=Path, default=config.BOOK_CATALOG_PATH)
    parser.add_argument("--book", type=int, default=None)
    parser.add_argument("--books", type=str, default=None)
    parser.add_argument("--max-books", type=int, default=20)

    args = parser.parse_args()
    regions = safe_json.load_json(args.regions_path, {})

    if args.book is not None:
        outputs = composite_all_variants(
            book_number=args.book,
            input_dir=args.input_dir,
            generated_dir=args.generated_dir,
            output_dir=args.output_dir,
            regions=regions,
            catalog_path=args.catalog_path,
        )
        logger.info("Composited %d files for book %s", len(outputs), args.book)
        return 0

    books = _parse_books(args.books)
    summary = batch_composite(
        input_dir=args.input_dir,
        generated_dir=args.generated_dir,
        output_dir=args.output_dir,
        regions_path=args.regions_path,
        book_numbers=books,
        max_books=args.max_books,
        catalog_path=args.catalog_path,
    )
    logger.info("Batch compositing summary: %s", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
