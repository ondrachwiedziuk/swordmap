#!/usr/bin/env python3
"""Generate A5 PDF papers with QR codes for game zones."""

import json
import hashlib
import argparse
import subprocess
import os

SECRET = "swordmap-tajny-klic"
BASE_URL = "https://smazeny.pull.cz/c/"
CONFIG = os.path.join(os.path.dirname(__file__), "..", "game_config.json")


def make_signature(zone_id: str) -> str:
    return hashlib.sha256(f"{zone_id}-{SECRET}".encode()).hexdigest()[:3].upper()


def generate_tex(config_path: str, num_spare: int) -> str:
    with open(config_path) as f:
        config = json.load(f)

    lines = []
    notice = (
        r"Toto je stanoviště pro hru na soustředění Korespondenčního semináře "
        r"z programování pořádaného Matematicko-fyzikální fakultou Univerzity Karlovy. "
        r"Prosím neničte jej. Sami je odstraníme nejpozději 25.\thinspace 4.\thinspace 2026. Děkujeme."
    )

    header = (
        r"\hbox to \hsize{"
        r"\vbox{\hsize=0.7\hsize " + notice + r"}"
        r"\hfil"
        r"\vbox to 0pt{\vss\pdfrefximage\hippoimg\vss}"
        r"}"
    )

    lines.append(r"""\input ucwmac2.tex
\input qrcode.tex
\qrset{height=8cm, level=H, tight, silent}

\hsize=98mm
\pdfpagewidth=148mm
\vsize=145mm
\pdfpageheight=210mm

\ucwmodule{ofs}
\chyph
\advance\hsize 3cm \hoffset -1.5cm
\advance\vsize 4cm \voffset -2cm
\parskip = 5pt
\parindent = 0pt

\def\center{\leftskip=0pt plus 1fill\relax\rightskip=\leftskip\relax}

\pdfximage height 2cm {hippo_game.epdf}
\edef\hippoimg{\the\pdflastximage}
""")

    # Zone pages
    for zone in config["zones"]:
        zid = str(zone["id"])
        sig = make_signature(zid)
        name = zone["name"]
        url = f"{BASE_URL}{zid}{sig}"
        lines.append(f"""
{header}
\\vskip 2pt
\\hrule
\\vskip 30pt
\\vfill

{{
\\center
{{\\settextsize{{50}}{name}}}

\\vskip 40pt

\\hbox to \\hsize{{\\hfil\\qrcode{{{url}}}\\hfil}}

\\vskip 40pt

{{\\settextsize{{50}}{zid}{sig}}}

\\vfill\\break
}}
""")

    # Spare pages (blank name area for writing by hand)
    for i in range(1, num_spare + 1):
        sid = f"S{i}"
        sig = make_signature(sid)
        url = f"{BASE_URL}{sid}{sig}"
        lines.append(f"""
{header}
\\vskip 2pt
\\hrule
\\vskip 30pt
\\vfill

{{
\\center
\\vskip 50pt

\\vskip 40pt

\\hbox to \\hsize{{\\hfil\\qrcode{{{url}}}\\hfil}}

\\vskip 40pt

{{\\settextsize{{50}}{sid}{sig}}}

\\vfill\\break
}}
""")

    lines.append(r"\bye")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate zone papers with QR codes")
    parser.add_argument("-c", "--config", default=CONFIG, help="Path to game_config.json")
    parser.add_argument("-s", "--spare", type=int, default=10, help="Number of spare blank pages")
    parser.add_argument("-o", "--output", default="zone-papers.tex", help="Output .tex file")
    args = parser.parse_args()

    tex = generate_tex(args.config, args.spare)

    with open(args.output, "w") as f:
        f.write(tex)

    print(f"Generated {args.output} with {args.spare} spare pages")

    output_dir = os.path.dirname(os.path.abspath(args.output))
    result = subprocess.run(
        ["pdfcsplain", os.path.abspath(args.output)],
        cwd=output_dir,
    )
    if result.returncode != 0:
        raise SystemExit(f"pdfcsplain failed with exit code {result.returncode}")

    pdf = os.path.splitext(args.output)[0] + ".pdf"
    print(f"Generated {pdf}")


if __name__ == "__main__":
    main()
