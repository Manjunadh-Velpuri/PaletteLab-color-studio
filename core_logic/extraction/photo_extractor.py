"""
PaletteLab Photo Palette Extractor.
Extracts dominant, vibrant, representative color palettes from photo images
using fast adaptive K-Means clustering over image color pixels, and locates
their exact spatial coordinates for circular target pinning.
"""

import math
import random
from pathlib import Path
from typing import List, Tuple, Union, Dict, Any
from PIL import Image

from core_logic.core.color_utils import hex_from_rgb


def extract_palette_with_positions(image_input: Union[str, Path, Image.Image], num_colors: int = 6) -> List[Dict[str, Any]]:
    """
    Extract K dominant colors and their spatial (rel_x, rel_y) coordinates on the image.
    Returns list of dicts: {"hex": "#RRGGBB", "rel_x": float, "rel_y": float, "rgb": (r, g, b)}
    """
    if isinstance(image_input, (str, Path)):
        path = Path(image_input)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {path}")
        img = Image.open(str(path)).convert("RGB")
    else:
        img = image_input.convert("RGB")

    w_orig, h_orig = img.size

    # Downsample for clustering
    sample_w = 200
    sample_h = max(1, int(200 * h_orig / max(1, w_orig)))
    img_small = img.resize((sample_w, sample_h), Image.Resampling.BOX)

    pixels_with_pos: List[Tuple[Tuple[int, int, int], float, float]] = []
    for y in range(sample_h):
        for x in range(sample_w):
            rgb = img_small.getpixel((x, y))
            rel_x = (x + 0.5) / sample_w
            rel_y = (y + 0.5) / sample_h
            pixels_with_pos.append((rgb, rel_x, rel_y))

    if not pixels_with_pos:
        return []

    # Sample subset
    sample_size = min(2500, len(pixels_with_pos))
    sampled = random.sample(pixels_with_pos, sample_size)

    k = max(2, min(num_colors, 16))

    # K-Means++ initialization
    centroids: List[Tuple[float, float, float]] = [sampled[0][0]]
    for _ in range(1, k):
        distances = []
        for p, rx, ry in sampled:
            min_d2 = min((p[0]-c[0])**2 + (p[1]-c[1])**2 + (p[2]-c[2])**2 for c in centroids)
            distances.append(min_d2)
        total_d2 = sum(distances)
        if total_d2 == 0:
            centroids.append(random.choice(sampled)[0])
            continue
        r_val = random.uniform(0, total_d2)
        accum = 0.0
        chosen = sampled[-1][0]
        for (p, rx, ry), d2 in zip(sampled, distances):
            accum += d2
            if accum >= r_val:
                chosen = p
                break
        centroids.append((float(chosen[0]), float(chosen[1]), float(chosen[2])))

    # Iterative K-Means refinement
    for _ in range(7):
        clusters: List[List[Tuple[Tuple[int, int, int], float, float]]] = [[] for _ in range(k)]
        for item in sampled:
            p = item[0]
            best_idx = 0
            best_dist = float("inf")
            for c_idx, c in enumerate(centroids):
                dist = (p[0]-c[0])**2 + (p[1]-c[1])**2 + (p[2]-c[2])**2
                if dist < best_dist:
                    best_dist = dist
                    best_idx = c_idx
            clusters[best_idx].append(item)

        new_centroids = []
        for c_idx in range(k):
            cluster = clusters[c_idx]
            if cluster:
                avg_r = sum(it[0][0] for it in cluster) / len(cluster)
                avg_g = sum(it[0][1] for it in cluster) / len(cluster)
                avg_b = sum(it[0][2] for it in cluster) / len(cluster)
                new_centroids.append((avg_r, avg_g, avg_b))
            else:
                new_centroids.append(centroids[c_idx])
        centroids = new_centroids

    # Find the representative sample point closest to each centroid
    results: List[Dict[str, Any]] = []
    seen_hex = set()

    for c in centroids:
        best_p = sampled[0]
        best_dist = float("inf")
        for item in sampled:
            p = item[0]
            dist = (p[0]-c[0])**2 + (p[1]-c[1])**2 + (p[2]-c[2])**2
            if dist < best_dist:
                best_dist = dist
                best_p = item

        hex_c = hex_from_rgb((c[0], c[1], c[2]))
        if hex_c not in seen_hex:
            seen_hex.add(hex_c)
            results.append({
                "hex": hex_c,
                "rel_x": best_p[1],
                "rel_y": best_p[2],
                "rgb": (round(c[0]), round(c[1]), round(c[2]))
            })

    # Sort by luminance
    def luminance(item: Dict[str, Any]) -> float:
        rgb = item["rgb"]
        return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]

    results.sort(key=luminance)
    return results
