#!/usr/bin/env python3
"""Generate PNG images with QR codes for game zones.

Each zone produces a single 384px-wide PNG containing:
  - the zone name at the top, in bold text
  - a QR code below it, with minimal side margins
  - the place code (zone id + signature) below the QR code, in large text
"""

import json
import hashlib
import argparse
import os

import qrcode
from PIL import Image, ImageDraw, ImageFont

SECRET = "17fm!5nj(gzjv)uvtffhijj9ojgrderfh90kbte2(5f3q8c7=az_17rs9@2t1f"
BASE_URL = "https://game.matfyzak.cz/c/"
CONFIG = os.path.join(os.path.dirname(__file__), "..", "game_config.json")

# Output image geometry
IMG_WIDTH = 384
MARGIN = 8  # minimal horizontal margin around the QR code
PADDING_TOP = 16
PADDING_BOTWEEN = 14  # spacing between sections
PADDING_BOTTOM = 16
BG_COLOR = "white"
FG_COLOR = "black"

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

NAME_FONT_SIZE = 60
CODE_FONT_SIZE = 60


def make_signature(zone_id: str) -> str:
    return hashlib.sha256(f"{zone_id}-{SECRET}".encode()).hexdigest()[:3].upper()


def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int):
    """Greedy word-wrap text to fit within max_width, returning a list of lines."""
    words = text.split()
    if not words:
        return [""]

    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def make_qr_image(data: str, target_width: int) -> Image.Image:
    """Create a QR code image scaled to exactly target_width (square)."""
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        border=1,  # minimal quiet zone
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img = img.resize((target_width, target_width), Image.NEAREST)
    return img


def render_zone_png(name: str, code_text: str, url: str, output_path: str) -> None:
    draw_dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    name_font = load_font(FONT_BOLD, NAME_FONT_SIZE)
    code_font = load_font(FONT_REGULAR, CODE_FONT_SIZE)

    qr_width = IMG_WIDTH - 2 * MARGIN
    qr_img = make_qr_image(url, qr_width)

    max_text_width = IMG_WIDTH - 2 * MARGIN

    # Wrap the name if it's a real name (spare pages pass an empty string)
    name_lines = wrap_text(draw_dummy, name, name_font, max_text_width) if name else []

    # Measure line heights
    def line_height(font: ImageFont.FreeTypeFont) -> int:
        bbox = draw_dummy.textbbox((0, 0), "Ay", font=font)
        return bbox[3] - bbox[1]

    name_line_h = line_height(name_font) if name_lines else 0
    code_line_h = line_height(code_font)

    name_block_h = len(name_lines) * name_line_h + max(0, len(name_lines) - 1) * 4

    total_height = (
        PADDING_TOP
        + name_block_h
        + (PADDING_BOTWEEN if name_lines else 0)
        + qr_width
        + PADDING_BOTWEEN
        + code_line_h
        + PADDING_BOTTOM
    )

    img = Image.new("RGB", (IMG_WIDTH, total_height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    y = PADDING_TOP

    # Name (bold), centered, possibly multi-line
    for line in name_lines:
        bbox = draw.textbbox((0, 0), line, font=name_font)
        w = bbox[2] - bbox[0]
        x = (IMG_WIDTH - w) // 2
        draw.text((x, y), line, font=name_font, fill=FG_COLOR)
        y += name_line_h + 4

    if name_lines:
        y += PADDING_BOTWEEN - 4

    # QR code, centered horizontally with minimal margin
    qr_x = (IMG_WIDTH - qr_width) // 2
    img.paste(qr_img, (qr_x, y))
    y += qr_width + PADDING_BOTWEEN

    # Code text, centered
    bbox = draw.textbbox((0, 0), code_text, font=code_font)
    w = bbox[2] - bbox[0]
    x = (IMG_WIDTH - w) // 2
    draw.text((x, y), code_text, font=code_font, fill=FG_COLOR)

    img.save(output_path)


def generate_pngs(config_path: str, num_spare: int, output_dir: str) -> list:
    with open(config_path) as f:
        config = json.load(f)

    os.makedirs(output_dir, exist_ok=True)
    generated = []

    # Zone pages
    for zone in config["zones"]:
        zid = str(zone["id"])
        sig = make_signature(zid)
        name = zone["name"]
        url = f"{BASE_URL}{zid}{sig}"
        code_text = f"{zid}{sig}"
        out_path = os.path.join(output_dir, f"zone-{zid}.png")
        render_zone_png(name, code_text, url, out_path)
        generated.append(out_path)

    # Spare pages (no name; hand-written on paper later)
    for i in range(1, num_spare + 1):
        sid = f"S{i}"
        sig = make_signature(sid)
        url = f"{BASE_URL}{sid}{sig}"
        code_text = f"{sid}{sig}"
        out_path = os.path.join(output_dir, f"spare-{sid}.png")
        render_zone_png("", code_text, url, out_path)
        generated.append(out_path)

    return generated


def main():
    parser = argparse.ArgumentParser(description="Generate zone QR code PNGs")
    parser.add_argument("-c", "--config", default=CONFIG, help="Path to game_config.json")
    parser.add_argument("-s", "--spare", type=int, default=10, help="Number of spare blank pages")
    parser.add_argument("-o", "--output-dir", default="zone-pngs", help="Output directory for PNGs")
    args = parser.parse_args()

    generated = generate_pngs(args.config, args.spare, args.output_dir)

    print(f"Generated {len(generated)} PNG files in {args.output_dir}/")
    for path in generated:
        print(f"  {path}")


if __name__ == "__main__":
    main()