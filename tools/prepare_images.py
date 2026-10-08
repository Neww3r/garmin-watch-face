#!/usr/bin/env python3
"""Prépare les images du cadran pour la Forerunner 165 (AMOLED rond 390x390).

Usage :
    python3 tools/prepare_images.py scene chemin/vers/illustration.png [cx cy côté]
        cx cy côté : carré à découper dans l'image source, en pixels (centre et taille).
        Le carré peut déborder de l'image : les bords sont alors prolongés (bande étirée).
        Par défaut, le plus grand carré centré.
        -> resources/drawables/bg_scene.png   (fond rond)
        -> resources/drawables/bg_aod.png     (contours seulement, pour l'always-on)
        -> resources/drawables/umbrella/*.png (parapluie de Satsuki, un par palier de batterie)
        -> resources/drawables/launcher_icon.png

    python3 tools/prepare_images.py icons   (après « scene »)
        -> resources/drawables/icons/*.png    (météo, Material Symbols Rounded)
"""
import colorsys
import json
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

SIZE = 390
LAUNCHER = 54
AOD_MAX_LIT = 0.10
AOD_TARGET_LIT = 0.05
AOD_MEDIAN = 7
AOD_BRIGHTNESS = 110
EDGE_STRIP = 60
SS = 4  # rendu à 4x puis réduction, pour un anticrénelage propre

SUNLIT_FUR = (87, 91, 78)  # icône météo : fourrure de Totoro au soleil (flanc gauche, 112/117/100), foncée de 22 %
WEATHER_ICON = 90
ALPHA_CUTOFF = 40  # sur 255 : en dessous, le pixel d'une icône devient transparent

ROOT = Path(__file__).resolve().parent.parent
DRAWABLES = ROOT / "resources" / "drawables"
LAYOUT = json.loads((ROOT / "resources" / "layout" / "layout.json").read_text())


def circle_mask(size):
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    return mask


def crop_reflect(img, box):
    """Découpe box dans img ; ce qui dépasse est rempli par une bande du bord, retournée et étirée.

    La bande fait au plus EDGE_STRIP pixels, pour ne pas dupliquer les éléments proches
    du bord (le panneau de l'arrêt de bus, par exemple).
    """
    x0, y0, x1, y1 = box
    left, top = max(0, -x0), max(0, -y0)
    right, bottom = max(0, x1 - img.width), max(0, y1 - img.height)
    w, h = img.size
    canvas = Image.new(img.mode, (w + left + right, h + top + bottom))
    canvas.paste(img, (left, top))
    if left:
        strip = img.crop((0, 0, min(left, EDGE_STRIP), h))
        canvas.paste(ImageOps.mirror(strip).resize((left, h), Image.LANCZOS), (0, top))
    if right:
        strip = img.crop((w - min(right, EDGE_STRIP), 0, w, h))
        canvas.paste(ImageOps.mirror(strip).resize((right, h), Image.LANCZOS), (left + w, top))
    full_w = canvas.width
    if top:
        strip = canvas.crop((0, top, full_w, top + min(top, EDGE_STRIP)))
        canvas.paste(ImageOps.flip(strip).resize((full_w, top), Image.LANCZOS), (0, 0))
    if bottom:
        strip = canvas.crop((0, top + h - min(bottom, EDGE_STRIP), full_w, top + h))
        canvas.paste(ImageOps.flip(strip).resize((full_w, bottom), Image.LANCZOS), (0, top + h))
    return canvas.crop((x0 + left, y0 + top, x1 + left, y1 + top))


def to_round(img, crop=None):
    """Recadre en carré SIZE x SIZE (au centre, ou sur crop = (cx, cy, côté)), noir hors du cercle."""
    img = img.convert("RGB")
    if crop:
        cx, cy, side = crop
        img = crop_reflect(img, (cx - side // 2, cy - side // 2, cx + side // 2, cy + side // 2))
    img = ImageOps.fit(img, (SIZE, SIZE), Image.LANCZOS)
    out = Image.new("RGB", (SIZE, SIZE), "black")
    out.paste(img, (0, 0), circle_mask(SIZE))
    return out


def make_aod(scene):
    """Contours de la scène en gris sombre, seuil ajusté pour viser AOD_TARGET_LIT.

    Le filtre médian efface les détails fins (pluie) pour ne garder que les grandes formes ;
    le bord du cercle est masqué pour ne pas dessiner un anneau.
    """
    edges = scene.convert("L").filter(ImageFilter.MedianFilter(AOD_MEDIAN)).filter(ImageFilter.FIND_EDGES)
    inner = circle_mask(SIZE).filter(ImageFilter.MinFilter(9))
    edges = Image.composite(edges, Image.new("L", (SIZE, SIZE), 0), inner)
    histogram = edges.histogram()
    budget = AOD_TARGET_LIT * SIZE * SIZE
    lit = 0
    threshold = 255
    while threshold > 0 and lit + histogram[threshold] <= budget:
        lit += histogram[threshold]
        threshold -= 1
    aod = edges.point(lambda v: AOD_BRIGHTNESS if v > threshold else 0)
    ratio = (SIZE * SIZE - aod.histogram()[0]) / (SIZE * SIZE)
    print(f"AOD : {ratio:.1%} de pixels allumés")
    assert ratio < AOD_MAX_LIT, "trop de pixels allumés pour l'always-on AMOLED"
    return Image.merge("RGB", (aod, aod, aod))


def save(img, name, colors=None):
    path = DRAWABLES / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if colors is None:
        img.save(path, optimize=True)
    else:
        img.quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.Dither.NONE).save(path, optimize=True)
    print(f"écrit {path.relative_to(ROOT)}")


def scene(src, crop=None):
    bg = to_round(Image.open(src), crop)
    save(bg, "bg_scene.png")
    for level in UMBRELLA_STEPS:
        save(umbrella_variant(bg, level), f"umbrella/umbrella_{level:03d}.png")
    save(make_aod(bg), "bg_aod.png", colors=2)
    save(bg.resize((LAUNCHER, LAUNCHER), Image.LANCZOS), "launcher_icon.png")


# --- Icônes météo : Material Symbols Rounded (Google, licence Apache 2.0), style contour ---
# https://github.com/google/material-design-icons — police téléchargée dans bin/cache/.

MATERIAL_URL = ("https://github.com/google/material-design-icons/raw/master/variablefont/"
                "MaterialSymbolsRounded%5BFILL,GRAD,opsz,wght%5D.ttf")
MATERIAL_FONT = ROOT / "bin" / "cache" / "material" / "MaterialSymbolsRounded.ttf"
MATERIAL_AXES = [0, 0, 48, 500]  # Fill (0 = contour), Grade, Optical size, Weight

# nom du fichier : point de code du glyphe
WEATHER = {
    "clear": 0xF157,         # clear_day
    "night": 0xF159,         # clear_night
    "partly": 0xF172,        # partly_cloudy_day
    "partly_night": 0xF174,  # partly_cloudy_night
    "cloudy": 0xF15C,        # cloud
    "rain": 0xF176,          # rainy
    "snow": 0xE2CD,          # weather_snowy
    "storm": 0xEBDB,         # thunderstorm
    "fog": 0xE818,           # foggy
}


def material_font(size):
    if not MATERIAL_FONT.exists():
        MATERIAL_FONT.parent.mkdir(parents=True, exist_ok=True)
        print(f"téléchargement de {MATERIAL_URL}")
        urllib.request.urlretrieve(MATERIAL_URL, MATERIAL_FONT)
    font = ImageFont.truetype(str(MATERIAL_FONT), size)
    font.set_variation_by_axes(MATERIAL_AXES)
    return font


def glyph_icon(code, size=WEATHER_ICON, color=SUNLIT_FUR):
    """Rend un glyphe Material centré, à SS fois la taille puis réduit."""
    big = Image.new("RGBA", (size * SS, size * SS), (0, 0, 0, 0))
    ImageDraw.Draw(big).text((size * SS // 2, size * SS // 2), chr(code), font=material_font(size * SS),
                             fill=color, anchor="mm")
    return big.resize((size, size), Image.BOX)


def blend_on(img, under):
    """Pose l'icône (opaque) sur l'image du fond située dessous, pour que ses bords
    anticrénelés se fondent dans le fond. La transparence du résultat est binaire : les bitmaps Garmin n'ont qu'une transparence tout-ou-rien, et le
    compilateur tramerait des bords semi-transparents (contours en pointillés)."""
    solid = Image.alpha_composite(under, img)
    solid.putalpha(img.getchannel("A").point(lambda a: 255 if a > ALPHA_CUTOFF else 0))
    return solid


# --- Parapluie de Satsuki recoloré selon la batterie (vert à 100 %, rouge d'origine à 0 %) ---

UMBRELLA_SIZE = (113, 68)
UMBRELLA_BOX = (LAYOUT["umbrella"][0], LAYOUT["umbrella"][1],
                LAYOUT["umbrella"][0] + UMBRELLA_SIZE[0], LAYOUT["umbrella"][1] + UMBRELLA_SIZE[1])
UMBRELLA_ZONES = [(68, 200, 181, 243), (112, 243, 126, 267)]  # toile, puis manche jusqu'à la main
UMBRELLA_HUE = 1  # teinte d'origine du parapluie, en degrés
UMBRELLA_FULL_HUE = 115  # teinte à 100 % de batterie (vert)
UMBRELLA_STEPS = range(0, 101, 10)
UMBRELLA_DESATURATE = 0.2  # désaturation à 100 %, proportionnelle au niveau
UMBRELLA_DARKEN = 0.12  # assombrissement à 100 % (vert un peu plus foncé)
UMBRELLA_LUMA_MATCH = 0.5  # 1 = même clarté que le rouge d'origine, 0 = aucune correction


def umbrella_weight(r, g, b):
    """Appartenance (0 à 1) d'un pixel au rouge du parapluie, avec des bords adoucis."""
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    hue = (h * 360 + 180) % 360 - 180  # -180..180, le rouge autour de 0
    hue_w = max(0.0, min(1.0, (14 - abs(hue - UMBRELLA_HUE)) / 6))
    sat_w = max(0.0, min(1.0, (s - 0.22) / 0.15))
    val_w = max(0.0, min(1.0, (v - 0.18) / 0.12))
    return hue_w * sat_w * val_w


def umbrella_variant(scene, level):
    """Rectangle UMBRELLA_BOX du fond avec le parapluie à la teinte du niveau de batterie."""
    x0, y0, x1, y1 = UMBRELLA_BOX
    img = scene.convert("RGB").crop(UMBRELLA_BOX)
    shift = (UMBRELLA_FULL_HUE * level / 100 - UMBRELLA_HUE) / 360
    px = img.load()
    for zx0, zy0, zx1, zy1 in UMBRELLA_ZONES:
        for y in range(zy0 - y0, zy1 - y0):
            for x in range(zx0 - x0, zx1 - x0):
                r, g, b = px[x, y]
                w = umbrella_weight(r, g, b)
                if w == 0:
                    continue
                h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                new = colorsys.hsv_to_rgb((h + shift) % 1.0, s * (1 - UMBRELLA_DESATURATE * level / 100), v)
                # Rapproche la clarté perçue de celle du rouge d'origine (le vert et le jaune
                # paraîtraient sinon fluo), un peu plus sombre vers le vert.
                ratio = (luma(r / 255, g / 255, b / 255) / max(luma(*new), 1e-6)) ** UMBRELLA_LUMA_MATCH
                ratio *= 1 - UMBRELLA_DARKEN * level / 100
                new = [min(1.0, c * ratio) for c in new]
                px[x, y] = tuple(round(o + (n * 255 - o) * w) for o, n in zip((r, g, b), new))
    return img


def luma(r, g, b):
    return 0.299 * r + 0.587 * g + 0.114 * b


def icons():
    """À lancer après « scene » : les icônes sont mélangées avec la couleur du fond sous elles."""
    # L'icône a une position fixe : ses bords anticrénelés sont mélangés avec les vrais
    # pixels du fond sous elle.
    cx, cy = LAYOUT["weather"]
    left, top = cx - WEATHER_ICON // 2, cy - WEATHER_ICON // 2
    under = Image.open(DRAWABLES / "bg_scene.png").convert("RGBA").crop(
        (left, top, left + WEATHER_ICON, top + WEATHER_ICON))
    for name, code in WEATHER.items():
        save(blend_on(glyph_icon(code), under), f"icons/weather_{name}.png")


if __name__ == "__main__":
    if len(sys.argv) in (3, 6) and sys.argv[1] == "scene":
        scene(sys.argv[2], tuple(int(v) for v in sys.argv[3:]) or None)
    elif len(sys.argv) == 2 and sys.argv[1] == "icons":
        icons()
    else:
        print(__doc__)
        sys.exit(1)
