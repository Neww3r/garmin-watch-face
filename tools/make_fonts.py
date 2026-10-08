#!/usr/bin/env python3
"""Génère les polices bitmap (format BMFont) du cadran à partir de SF Compact Rounded.

Usage :
    python3 tools/make_fonts.py

Chaque police a une hauteur de capitales (ou de chiffres) donnée. Avec une largeur de
référence, elle est en plus calibrée sur la maquette : l'espacement des lettres est ajusté,
puis, si les lettres se toucheraient, les glyphes sont compressés. Sans largeur de
référence, la police garde ses proportions et son espacement naturels.
La boîte de chaque police fait exactement les capitales plus OVERSHOOT en haut et en bas :
le cadran centre un texte en plaçant son haut à cy - hauteur / 2 (TotoroView.mc).
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_FILE = "/System/Library/Fonts/SFCompactRounded.ttf"
FONTS = Path(__file__).resolve().parent.parent / "resources" / "fonts"
OVERSHOOT = 1  # marge en haut et en bas pour les lettres rondes (O, C, 8…)
MIN_TRACKING = -2.0
MIN_SPACE = 0.45  # largeur minimale de l'espace, en fraction de la hauteur des capitales
INK_THRESHOLD = 16  # en dessous, un pixel n'est pas considéré comme de l'encre
SS = 4  # rendu à 4x puis réduction, pour un anticrénelage propre

# nom : (graisse, caractères, hauteur des capitales, texte de référence, largeur de référence)
# Sans largeur de référence (None), la police garde ses proportions et son espacement naturels.
SPECS = {
    "time": ("Medium", "0123456789:", 64, "15:58", None),
    "date": ("Semibold", "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ", 14, "JEU 8 OCT", 108),
}


def load(weight, size):
    font = ImageFont.truetype(FONT_FILE, size)
    font.set_variation_by_name(weight)
    return font


def cap_height(font, chars):
    """Hauteur des capitales, ou des chiffres pour une police sans lettres."""
    return -font.getbbox("H" if "H" in chars else "0", anchor="ls")[1]


def calibrate(weight, chars, target_cap, ref_text, ref_width):
    """Renvoie la police (à SS fois la taille finale), l'espacement et la compression horizontale."""
    size = 10.0 * SS
    for _ in range(10):
        size *= target_cap * SS / cap_height(load(weight, size), chars)
    font = load(weight, size)
    if ref_width is None:
        return font, 0.0, 1.0
    natural = font.getlength(ref_text) / SS
    gaps = max(len(ref_text) - 1, 1)
    tracking = (ref_width - natural) / gaps
    squeeze = 1.0
    if tracking < MIN_TRACKING:
        tracking = MIN_TRACKING
        squeeze = (ref_width - tracking * gaps) / natural
    return font, tracking, squeeze


def render_glyph(font, ch, squeeze, base, line_height):
    """Rend un glyphe sur toute la hauteur de ligne, ligne de base et origine calées sur la grille.

    Rendre chaque glyphe à sa propre hauteur puis arrondir sa position décalait certaines
    lettres d'un pixel ; ici tous partagent la même ligne de base (yoffset = 0).
    Renvoie le glyphe recadré horizontalement et son décalage par rapport à l'origine.
    """
    left, _, right, _ = font.getbbox(ch, anchor="ls")
    big = Image.new("L", (right - left + 2 * SS, line_height * SS), 0)
    origin = SS - left
    ImageDraw.Draw(big).text((origin, base * SS), ch, font=font, fill=255, anchor="ls")
    if squeeze != 1.0:
        big = big.resize((round(big.width * squeeze), big.height), Image.BOX)
        origin *= squeeze
    # décale pour que l'origine tombe sur un pixel entier une fois réduite
    shift = round(-origin % SS)
    aligned = Image.new("L", (-(-(big.width + shift) // SS) * SS, big.height), 0)
    aligned.paste(big, (shift, 0))
    # moyenne de surface : pas de halo autour des lettres, contrairement à Lanczos
    small = aligned.resize((aligned.width // SS, line_height), Image.BOX)
    x0, _, x1, _ = small.point(lambda v: 255 if v > INK_THRESHOLD else 0).getbbox()
    return small.crop((x0, 0, x1, line_height)), x0 - round((origin + shift) / SS)


def build(name, weight, chars, target_cap, ref_text, ref_width):
    font, tracking, squeeze = calibrate(weight, chars, target_cap, ref_text, ref_width)
    cap = round(cap_height(font, chars) / SS)
    base = cap + OVERSHOOT
    line_height = cap + 2 * OVERSHOOT

    glyphs = []
    for ch in chars:
        advance = round(font.getlength(ch) * squeeze / SS + tracking)
        if ch == " ":
            glyphs.append((ch, None, 0, 0, max(advance, round(MIN_SPACE * cap))))
        else:
            img, xoffset = render_glyph(font, ch, squeeze, base, line_height)
            # Garmin coupe le texte à la somme des avancées : le glyphe doit y tenir
            # (sinon le dernier caractère, comme le « % », est rogné).
            glyphs.append((ch, img, xoffset, 0, max(advance, xoffset + img.width)))

    width = sum(g[1].width + 2 for g in glyphs if g[1]) + 2
    height = max(g[1].height for g in glyphs if g[1]) + 2
    page = Image.new("L", (width, height), 0)
    lines = []
    x = 1
    for ch, img, xoffset, yoffset, advance in glyphs:
        if img:
            page.paste(img, (x, 1))
            lines.append(f"char id={ord(ch)} x={x} y=1 width={img.width} height={img.height} "
                         f"xoffset={xoffset} yoffset={yoffset} xadvance={advance} page=0 chnl=15")
            x += img.width + 2
        else:
            lines.append(f"char id={ord(ch)} x=0 y=0 width=0 height=0 "
                         f"xoffset=0 yoffset=0 xadvance={advance} page=0 chnl=15")

    FONTS.mkdir(parents=True, exist_ok=True)
    page.save(FONTS / f"{name}.png", optimize=True)
    header = [
        f'info face="SF Compact Rounded {weight}" size={line_height} bold=0 italic=0 charset="" unicode=1 '
        f"stretchH=100 smooth=1 aa=1 padding=0,0,0,0 spacing=1,1",
        f"common lineHeight={line_height} base={base} scaleW={width} scaleH={height} pages=1 packed=0 "
        f"alphaChnl=1 redChnl=0 greenChnl=0 blueChnl=0",
        f'page id=0 file="{name}.png"',
        f"chars count={len(lines)}",
    ]
    (FONTS / f"{name}.fnt").write_text("\n".join(header + lines) + "\n")
    print(f"{name} : capitales {cap}px, espacement {tracking:+.1f}px, compression {squeeze:.2f}")


if __name__ == "__main__":
    for name, spec in SPECS.items():
        build(name, *spec)
