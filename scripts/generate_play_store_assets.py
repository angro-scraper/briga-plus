from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "store-assets" / "android"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 1080, 1920
CREAM = "#F9F7F2"
WHITE = "#FFFFFF"
GREEN = "#315C45"
DARK_GREEN = "#173F31"
LIGHT_GREEN = "#E7F2EA"
RED = "#E63946"
ORANGE = "#F4A261"
TEAL = "#2A9D8F"
BLUE = "#2676B8"
PURPLE = "#6F5BA7"
TEXT = "#20352E"
MUTED = "#62716B"
BORDER = "#DDE5DF"


def font(size, bold=False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)


def round_rect(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def shadow_card(canvas, box, radius=34, fill=WHITE, shadow=(30, 60, 45, 26)):
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x1, y1, x2, y2 = box
    d.rounded_rectangle((x1, y1 + 12, x2, y2 + 18), radius=radius, fill=shadow)
    layer = layer.filter(ImageFilter.GaussianBlur(18))
    canvas.alpha_composite(layer)
    ImageDraw.Draw(canvas).rounded_rectangle(box, radius=radius, fill=fill, outline=BORDER, width=2)


def text(draw, xy, value, size, color=TEXT, bold=False, anchor=None):
    draw.text(xy, value, font=font(size, bold), fill=color, anchor=anchor)


def wrap(draw, value, max_width, size, bold=False):
    words = value.split()
    lines, line = [], ""
    f = font(size, bold)
    for word in words:
        candidate = f"{line} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=f)[2] <= max_width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def draw_icon(draw, kind, center, color, bg):
    cx, cy = center
    draw.ellipse((cx - 48, cy - 48, cx + 48, cy + 48), fill=bg)
    if kind == "heart":
        draw.ellipse((cx - 26, cy - 15, cx + 1, cy + 14), fill=color)
        draw.ellipse((cx - 1, cy - 15, cx + 26, cy + 14), fill=color)
        draw.polygon([(cx - 26, cy), (cx + 26, cy), (cx, cy + 32)], fill=color)
    elif kind == "pill":
        draw.rounded_rectangle((cx - 28, cy - 14, cx + 28, cy + 14), radius=14, outline=color, width=6)
        draw.line((cx, cy - 13, cx, cy + 13), fill=color, width=5)
    elif kind == "phone":
        draw.arc((cx - 28, cy - 30, cx + 28, cy + 30), 115, 245, fill=color, width=8)
        draw.ellipse((cx - 31, cy + 13, cx - 17, cy + 29), fill=color)
        draw.ellipse((cx + 17, cy - 29, cx + 31, cy - 13), fill=color)
    elif kind == "check":
        draw.ellipse((cx - 27, cy - 27, cx + 27, cy + 27), outline=color, width=6)
        draw.line((cx - 15, cy, cx - 3, cy + 13, cx + 20, cy - 15), fill=color, width=7, joint="curve")
    elif kind == "chat":
        draw.rounded_rectangle((cx - 29, cy - 23, cx + 29, cy + 19), radius=13, outline=color, width=6)
        draw.polygon([(cx - 8, cy + 18), (cx - 21, cy + 32), (cx + 2, cy + 20)], fill=color)
        for dx in (-13, 0, 13):
            draw.ellipse((cx + dx - 3, cy - 4, cx + dx + 3, cy + 2), fill=color)
    elif kind == "doc":
        draw.rounded_rectangle((cx - 24, cy - 30, cx + 24, cy + 30), radius=6, outline=color, width=5)
        for yy in (-12, 2, 16):
            draw.line((cx - 13, cy + yy, cx + 13, cy + yy), fill=color, width=4)
    elif kind == "pin":
        draw.ellipse((cx - 22, cy - 28, cx + 22, cy + 16), outline=color, width=6)
        draw.ellipse((cx - 6, cy - 12, cx + 6, cy), fill=color)
        draw.polygon([(cx - 15, cy + 8), (cx + 15, cy + 8), (cx, cy + 33)], fill=color)
    elif kind == "calendar":
        draw.rounded_rectangle((cx - 28, cy - 25, cx + 28, cy + 28), radius=7, outline=color, width=5)
        draw.line((cx - 28, cy - 8, cx + 28, cy - 8), fill=color, width=5)
        draw.line((cx - 15, cy - 31, cx - 15, cy - 18), fill=color, width=6)
        draw.line((cx + 15, cy - 31, cx + 15, cy - 18), fill=color, width=6)


def header(canvas, title, subtitle, senior=False):
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, W, 330), fill=GREEN)
    draw.ellipse((760, -170, 1180, 250), fill="#3B6C50")
    text(draw, (64, 76), title, 46, WHITE, True)
    text(draw, (64, 137), subtitle, 26, "#DCE9DF")
    if senior:
        round_rect(draw, (860, 66, 1008, 150), 42, "#4F755F", "#DDE9E1", 2)
        text(draw, (934, 108), "A+", 34, WHITE, True, "mm")
    else:
        draw.ellipse((892, 62, 1000, 170), fill="#F7DDC8")
        text(draw, (946, 116), "M", 42, DARK_GREEN, True, "mm")


def sos_button(canvas, y=275, label="SOS", sub="Pošalji GPS lokaciju i pozovi pomoć"):
    draw = ImageDraw.Draw(canvas)
    shadow_card(canvas, (48, y, 1032, y + 155), 38, RED, (185, 35, 45, 35))
    draw = ImageDraw.Draw(canvas)
    draw_icon(draw, "phone", (128, y + 78), WHITE, "#F45D68")
    text(draw, (205, y + 33), label, 55, WHITE, True)
    text(draw, (207, y + 98), sub, 25, WHITE, True)


def bottom_nav(canvas, active=0, items=("Početna", "Zdravlje", "Zadaci", "Poruke", "Meni")):
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 1742, W, H), fill=WHITE)
    draw.line((0, 1742, W, 1742), fill=BORDER, width=2)
    icons = ["heart", "pill", "calendar", "chat", "doc"]
    for i, label in enumerate(items):
        x = 108 + i * 216
        color = "#087A59" if i == active else "#7B8580"
        draw_icon(draw, icons[i], (x, 1797), color, "#FFFFFF")
        text(draw, (x, 1867), label, 22, color, i == active, "mm")


def screenshot_family():
    canvas = Image.new("RGBA", (W, H), CREAM)
    header(canvas, "Porodica Petrović", "Brinemo zajedno")
    sos_button(canvas, 270, "SOS za mene", "Šalje moju GPS lokaciju porodici")
    draw = ImageDraw.Draw(canvas)
    shadow_card(canvas, (48, 455, 1032, 700), 38, "#EFF6EC")
    draw_icon(draw, "check", (125, 530), "#16855E", WHITE)
    text(draw, (205, 487), "Jelena je odlično danas", 35, DARK_GREEN, True)
    text(draw, (205, 539), "Dnevna potvrda je stigla i porodica je obaveštena.", 24, MUTED)
    round_rect(draw, (205, 595, 950, 660), 18, "#F9FBF7", "#9AB59E", 2)
    text(draw, (238, 628), "Pogledaj detalje", 25, GREEN, True, "lm")
    text(draw, (912, 628), "›", 42, GREEN, False, "mm")
    text(draw, (55, 760), "Zdravlje danas", 33, DARK_GREEN, True)
    for i, (kind, title, value, sub, color, bg) in enumerate([
        ("heart", "Koraci", "3.240", "danas", TEAL, "#E5F5F1"),
        ("heart", "Puls", "72", "otkucaja/min", RED, "#FDEBEC"),
    ]):
        x1 = 48 + i * 510
        shadow_card(canvas, (x1, 820, x1 + 474, 1030), 34)
        draw_icon(draw, kind, (x1 + 83, 890), color, bg)
        text(draw, (x1 + 145, 858), title, 27, TEXT, True)
        text(draw, (x1 + 145, 905), value, 40, DARK_GREEN, True)
        text(draw, (x1 + 145, 958), sub, 21, MUTED)
    text(draw, (55, 1090), "Brzi pregled", 33, DARK_GREEN, True)
    cards = [
        ("pill", "2", "leka danas", ORANGE, "#FFF2D8"),
        ("calendar", "1", "zadatak", BLUE, "#E8F4FB"),
        ("chat", "3", "poruke", PURPLE, "#EFEAFB"),
        ("doc", "4", "dokumenta", TEAL, "#E5F5F1"),
    ]
    for i, (kind, val, label, color, bg) in enumerate(cards):
        x1 = 48 + (i % 2) * 510
        y1 = 1145 + (i // 2) * 230
        shadow_card(canvas, (x1, y1, x1 + 474, y1 + 200), 32)
        draw_icon(draw, kind, (x1 + 82, y1 + 80), color, bg)
        text(draw, (x1 + 150, y1 + 48), val, 42, DARK_GREEN, True)
        text(draw, (x1 + 150, y1 + 108), label, 25, MUTED)
    bottom_nav(canvas, 0)
    canvas.convert("RGB").save(OUT / "01-porodicni-panel.jpg", quality=94, optimize=True)


def screenshot_senior():
    canvas = Image.new("RGBA", (W, H), CREAM)
    header(canvas, "Dobro jutro, Jelena", "Tu smo uz vas, svaki dan", True)
    sos_button(canvas, 270, "SOS", "Jedan dodir šalje pomoć i tačnu lokaciju")
    draw = ImageDraw.Draw(canvas)
    shadow_card(canvas, (48, 460, 1032, 675), 38, "#EEF7EA")
    draw_icon(draw, "heart", (128, 568), "#16855E", "#D9EFD9")
    text(draw, (210, 512), "Dobro sam", 45, DARK_GREEN, True)
    text(draw, (210, 570), "Pritisnite i javite porodici kako se osećate", 25, MUTED)
    text(draw, (960, 566), "›", 52, GREEN, False, "mm")
    text(draw, (55, 740), "Moj dan", 33, DARK_GREEN, True)
    rows = [
        ("pill", "Moja terapija", "Sledeći lek u 14:00", ORANGE, "#FFF1D5"),
        ("phone", "Pozovi porodicu", "Brzo i lako", BLUE, "#E3F2FC"),
        ("doc", "Moj dnevnik zdravlja", "Beleške, simptomi i dokumenti", PURPLE, "#EEE9FA"),
        ("calendar", "Današnje obaveze", "1 zakazan pregled", TEAL, "#E3F4F0"),
    ]
    for i, (kind, title, sub, color, bg) in enumerate(rows):
        y1 = 795 + i * 205
        shadow_card(canvas, (48, y1, 1032, y1 + 170), 32)
        draw_icon(draw, kind, (128, y1 + 85), color, bg)
        text(draw, (210, y1 + 45), title, 34, DARK_GREEN, True)
        text(draw, (210, y1 + 98), sub, 24, MUTED)
        text(draw, (960, y1 + 86), "›", 48, GREEN, False, "mm")
    bottom_nav(canvas, 0, ("Moj dan", "Lekovi", "Pomoć", "Poruke", "Meni"))
    canvas.convert("RGB").save(OUT / "02-panel-cuvanog-lica.jpg", quality=94, optimize=True)


def screenshot_sos():
    canvas = Image.new("RGBA", (W, H), RED)
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((250, 210, 830, 790), fill="#FFFFFF18", outline="#FFFFFF55", width=6)
    draw_icon(draw, "pin", (540, 430), WHITE, "#FFFFFF25")
    text(draw, (540, 555), "SOS JE POSLAT", 56, WHITE, True, "mm")
    text(draw, (540, 635), "Porodica je odmah obaveštena", 30, WHITE, False, "mm")
    text(draw, (540, 690), "Lokacija: Bulevar oslobođenja, Vranje", 25, "#FFE5E7", False, "mm")
    shadow_card(canvas, (65, 875, 1015, 1230), 38, WHITE, (120, 0, 10, 50))
    draw = ImageDraw.Draw(canvas)
    text(draw, (110, 935), "Pomoć je na putu", 42, DARK_GREEN, True)
    text(draw, (110, 1000), "Članovi porodice vide vašu lokaciju i rutu.", 27, MUTED)
    round_rect(draw, (110, 1085, 970, 1170), 22, "#F8EBEC", "#EAB6BA", 2)
    text(draw, (540, 1128), "Pozovi hitan kontakt", 29, RED, True, "mm")
    round_rect(draw, (65, 1425, 1015, 1545), 30, "#B71C28", "#FFFFFF88", 2)
    text(draw, (540, 1485), "POZOVI ODMAH", 34, WHITE, True, "mm")
    round_rect(draw, (65, 1570, 1015, 1690), 30, "#FFFFFF24", WHITE, 3)
    text(draw, (540, 1630), "ALARM JE SLUČAJNO POKRENUT", 27, WHITE, True, "mm")
    text(draw, (540, 1815), "Briga+ • Niste sami", 24, "#FFE4E6", False, "mm")
    canvas.convert("RGB").save(OUT / "03-sos-lokacija.jpg", quality=94, optimize=True)


def screenshot_health():
    canvas = Image.new("RGBA", (W, H), CREAM)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, W, 250), fill=GREEN)
    text(draw, (62, 82), "‹", 60, WHITE)
    text(draw, (130, 96), "Zdravstveni dnevnik", 42, WHITE, True)
    text(draw, (130, 154), "Sve važne informacije na jednom mestu", 24, "#DDE9E1")
    shadow_card(canvas, (48, 300, 1032, 505), 34, "#EDF5E9")
    draw_icon(draw, "heart", (128, 398), "#16855E", WHITE)
    text(draw, (205, 345), "Kako se danas osećate?", 34, DARK_GREEN, True)
    text(draw, (205, 400), "Odlično", 29, GREEN, True)
    text(draw, (205, 452), "Porodica vidi samo ono što podelite.", 22, MUTED)
    text(draw, (55, 570), "Dokumenti", 33, DARK_GREEN, True)
    for i, (title, sub, kind, color, bg) in enumerate([
        ("Nalaz kardiologa", "PDF • 12. maj 2026.", "doc", PURPLE, "#EFEAFA"),
        ("Laboratorijski rezultati", "Fotografija • 8. maj 2026.", "doc", BLUE, "#E7F3FB"),
        ("Otpusna lista", "PDF • 2. april 2026.", "doc", TEAL, "#E4F4F0"),
    ]):
        y1 = 630 + i * 200
        shadow_card(canvas, (48, y1, 1032, y1 + 165), 30)
        draw_icon(draw, kind, (128, y1 + 82), color, bg)
        text(draw, (205, y1 + 40), title, 31, TEXT, True)
        text(draw, (205, y1 + 96), sub, 23, MUTED)
        text(draw, (958, y1 + 82), "›", 46, GREEN, False, "mm")
    text(draw, (55, 1275), "Beleške i simptomi", 33, DARK_GREEN, True)
    shadow_card(canvas, (48, 1335, 1032, 1515), 30)
    draw_icon(draw, "chat", (128, 1424), ORANGE, "#FFF1D8")
    text(draw, (205, 1380), "Danas se osećam dobro", 31, TEXT, True)
    text(draw, (205, 1435), "Bez bola i vrtoglavice.", 24, MUTED)
    round_rect(draw, (48, 1580, 1032, 1692), 28, GREEN)
    text(draw, (540, 1636), "+ Dodaj dokument ili belešku", 31, WHITE, True, "mm")
    bottom_nav(canvas, 1)
    canvas.convert("RGB").save(OUT / "04-zdravstveni-dnevnik.jpg", quality=94, optimize=True)


def feature_graphic():
    canvas = Image.new("RGBA", (1024, 500), CREAM)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((-70, -110, 610, 620), radius=190, fill=GREEN)
    draw.ellipse((715, -110, 1080, 255), fill="#E6F1E8")
    draw.ellipse((815, 275, 1090, 550), fill="#FBE2D2")
    logo = Image.open(ROOT / "static" / "briga-app-icon-512.png").convert("RGBA")
    logo.thumbnail((205, 205), Image.Resampling.LANCZOS)
    canvas.alpha_composite(logo, (75, 145))
    text(draw, (305, 155), "Briga+", 78, WHITE, True)
    text(draw, (310, 245), "Brinemo zajedno.", 36, "#F4E9D6", True)
    text(draw, (310, 295), "Svaki dan.", 36, "#F4E9D6", True)
    # Three calm feature bubbles on the light side.
    for center, kind, color, bg in [
        ((720, 185), "heart", "#16855E", "#E1F1E4"),
        ((850, 250), "pill", ORANGE, "#FFF0D5"),
        ((735, 355), "phone", RED, "#FDE8EA"),
    ]:
        draw_icon(draw, kind, center, color, bg)
    canvas.convert("RGB").save(OUT / "feature-graphic-1024x500.jpg", quality=95, optimize=True)


if __name__ == "__main__":
    feature_graphic()
    screenshot_family()
    screenshot_senior()
    screenshot_sos()
    screenshot_health()
    for path in sorted(OUT.glob("*")):
        with Image.open(path) as image:
            print(f"{path.name}: {image.size[0]}x{image.size[1]}, {path.stat().st_size} bytes")
