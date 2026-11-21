"""Build the Delegate & Defend demo video slides (1080x1920, 9:16).

Renders each slide as a PNG with PIL (real on-chain data + the Internet
Court, GenLayer, and MetaMask logos), then build_video.sh stitches them
into a <=45s mp4 with ffmpeg. Re-run after any re-deploy to refresh the data.
"""
import textwrap
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
FRAMES = HERE / "frames"
FRAMES.mkdir(exist_ok=True)

W, H = 1080, 1920
BG = (11, 16, 32)          # deep navy
CARD = (22, 30, 54)        # card navy
WHITE = (245, 247, 250)
MUTED = (168, 178, 198)
GREEN = (74, 222, 128)
RED = (248, 113, 113)
GOLD = (251, 191, 36)
BLUE = (96, 165, 250)
MONO = (147, 197, 253)

F = "/usr/share/fonts/truetype/dejavu/"
def font(name, size):
    return ImageFont.truetype(F + name, size)

F_TITLE = font("DejaVuSans-Bold.ttf", 96)
F_H1 = font("DejaVuSans-Bold.ttf", 72)
F_H2 = font("DejaVuSans-Bold.ttf", 54)
F_BODY = font("DejaVuSans.ttf", 44)
F_BODY_B = font("DejaVuSans-Bold.ttf", 44)
F_SMALL = font("DejaVuSans.ttf", 36)
F_MONO = font("DejaVuSansMono.ttf", 30)
F_MONO_SM = font("DejaVuSansMono.ttf", 26)
F_TAG = font("DejaVuSans-Bold.ttf", 34)

# ---- real on-chain data (Studio Next, chain 61997) ----
CONTRACT = "0xD6D0C6C90CCcED47835bf790Ea3a2BcD52be6437"
TX_GRANT = "0x4f838095a5f45c0148ee8256e88c5d0204e50b89cd1b7c9fce6844f53b4bcf54"
TX_OPEN1 = "0x33bce1811d2666513cee0df7f702a3a40e7e9cc3a23e418199a1e29c655001b4"
TX_CONFIRM1 = "0xdfc79aefa8eb7ced5daba8af1382a87f8ebc1559a78e339abcfc8bc03e6e51c1"
TX_DISPUTE2 = "0xc984a1afdc869484fc34ebbe9de21eb8a07c08c8b14a2d323ec6fa67fd3c6b0d"
TX_ADJUDICATE2 = "0x19f1e30989f9301770f3c9636e46dd6f0640c40239ce0a67c7bf2952d35f23b3"
TX_BLOCKED3 = "0x646b114f75901db2686f3f8429d506daadac6374a8effde07ddf6046c7f034a0"
VERDICT = ("The dispute gives a concrete account of non-delivery: no file, "
           "link, or message arrived in the three days after payment. The deal "
           "facts show no delivery by the seller, so the report was not "
           "delivered as promised.")


def short(h):
    return h[:10] + "..." + h[-8:]


def logo_png(name, width):
    """Render an SVG asset to a PNG of the given width (aspect preserved)."""
    out = FRAMES / (name + ".png")
    cairosvg.svg2png(url=str(ASSETS / (name + ".svg")), write_to=str(out),
                     output_width=width)
    return Image.open(out).convert("RGBA")


def new_slide():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([36, 36, W - 36, H - 36], radius=28, outline=(38, 50, 84), width=3)
    return img, d


def center_text(d, y, text, fnt, fill, width=W):
    d.text((width / 2, y), text, font=fnt, fill=fill, anchor="ma")


def wrap(d, x, y, text, fnt, fill, max_w, leading=1.35):
    """Word-wrap text into lines fitting max_w; returns y after last line."""
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    for line in lines:
        d.text((x, y), line, font=fnt, fill=fill)
        y += int(fnt.size * leading)
    return y


def logo_card(img, logo, cx, y, pad_x=36, pad_y=26):
    """Paste a logo centered on a white rounded card; returns bottom y."""
    d = ImageDraw.Draw(img)
    w, h = logo.size
    x0, y0 = cx - w // 2 - pad_x, y
    x1, y1 = cx + w // 2 + pad_x, y + h + pad_y * 2
    d.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=(255, 255, 255))
    img.paste(logo, (cx - w // 2, y + pad_y), logo)
    return y1


def tx_line(d, y, label, h):
    d.text((90, y), label, font=F_SMALL, fill=MUTED)
    d.text((90, y + 48), short(h), font=F_MONO, fill=MONO)
    return y + 110


def footer(d, text="Studio Next  •  chain 61997  •  DelegateCourt"):
    center_text(d, H - 130, text, F_SMALL, MUTED)


def slide1_title():
    img, d = new_slide()
    ic = logo_png("internet-court-logo", 560)
    gl = logo_png("genlayer-logo", 460)
    mm = logo_png("metamask-logo", 380)
    y = logo_card(img, ic, W // 2, 180) + 48
    y = logo_card(img, gl, W // 2, y) + 48
    y = logo_card(img, mm, W // 2, y) + 90
    center_text(d, y, "DELEGATE &", F_TITLE, WHITE)
    center_text(d, y + 120, "DEFEND", F_TITLE, GOLD)
    center_text(d, y + 280, "ERC-7710 delegations judged by", F_BODY, MUTED)
    center_text(d, y + 340, "GenLayer's Internet Court", F_BODY, MUTED)
    center_text(d, y + 470, "Mission 101  •  Partner Demo Lab", F_TAG, BLUE)
    footer(d)
    img.save(FRAMES / "s1.png")


def slide2_mandate():
    img, d = new_slide()
    center_text(d, 150, "1  •  THE MANDATE", F_TAG, BLUE)
    center_text(d, 230, "Delegator grants", F_H1, WHITE)
    center_text(d, 320, "an ERC-7710 mandate", F_H1, WHITE)
    y = 520
    rows = [
        ("Delegate agent", "0x6907…493C"),
        ("Spend cap", "0.10 GEN"),
        ("Per-deal cap", "0.06 GEN"),
        ("Max deals", "5"),
        ("Expiry", "30 days"),
    ]
    for label, val in rows:
        d.rounded_rectangle([90, y, W - 90, y + 108], radius=18, fill=CARD)
        d.text((130, y + 30), label, font=F_BODY, fill=MUTED)
        tw = d.textlength(val, font=F_BODY_B)
        d.text((W - 130 - tw, y + 30), val, font=F_BODY_B, fill=WHITE)
        y += 132
    y += 40
    d.text((90, y), "grant_delegation  →  status: active", font=F_BODY_B, fill=GREEN)
    y = tx_line(d, y + 80, "tx", TX_GRANT)
    footer(d)
    img.save(FRAMES / "s2.png")


def slide3_happy():
    img, d = new_slide()
    center_text(d, 150, "2  •  HAPPY PATH", F_TAG, GREEN)
    center_text(d, 230, "deal-001", F_H1, WHITE)
    y = wrap(d, 90, 380, "Logo design pack — 3 concepts, SVG + PNG", F_BODY, WHITE, W - 180)
    y = wrap(d, 90, y + 20, "Agent opens the deal under mandate-001.", F_BODY, MUTED, W - 180)
    y += 60
    d.rounded_rectangle([90, y, W - 90, y + 200], radius=24, fill=(20, 60, 38))
    center_text(d, y + 40, "DELIVERED", F_H1, GREEN)
    center_text(d, y + 130, "escrow released  •  0.03 GEN", F_BODY, WHITE)
    y += 280
    y = tx_line(d, y, "open_deal tx", TX_OPEN1)
    y = tx_line(d, y + 10, "confirm tx", TX_CONFIRM1)
    footer(d)
    img.save(FRAMES / "s3.png")


def slide4_dispute():
    img, d = new_slide()
    center_text(d, 150, "3  •  DISPUTE", F_TAG, RED)
    center_text(d, 230, "deal-002", F_H1, WHITE)
    y = wrap(d, 90, 380, "AI market-research report — 10 pages, English  •  0.05 GEN",
             F_BODY, WHITE, W - 180)
    y += 50
    card_top = y
    d.rounded_rectangle([90, card_top, W - 90, card_top + 380], radius=24, fill=CARD)
    wrap(d, 130, card_top + 36, "“The seller never sent the report. No file, no link, no message after payment. Three days passed and nothing was delivered.”",
         F_BODY, WHITE, W - 260)
    y = card_top + 380 + 70
    d.text((90, y), "Delegator disputes  →  status: disputed", font=F_BODY_B, fill=RED)
    y = tx_line(d, y + 80, "dispute tx", TX_DISPUTE2)
    center_text(d, y + 60, "The Internet Court convenes…", F_BODY, MUTED)
    footer(d)
    img.save(FRAMES / "s4.png")


def slide5_verdict():
    img, d = new_slide()
    center_text(d, 150, "4  •  THE VERDICT", F_TAG, GOLD)
    center_text(d, 230, "REFUNDED", F_H1, RED)
    y = 380
    d.text((90, y), "Court verdict (on-chain, verbatim):", font=F_BODY_B, fill=WHITE)
    y += 70
    card_top = y
    d.rounded_rectangle([90, card_top, W - 90, card_top + 520], radius=24, fill=CARD)
    wrap(d, 130, card_top + 36, "“" + VERDICT + "”", F_BODY, WHITE, W - 260)
    y = card_top + 520 + 60
    d.text((90, y), "assessment: not_delivered", font=F_BODY_B, fill=WHITE)
    d.text((90, y + 60), "decision: refund", font=F_BODY_B, fill=WHITE)
    y = tx_line(d, y + 140, "adjudicate tx", TX_ADJUDICATE2)
    footer(d)
    img.save(FRAMES / "s5.png")


def slide6_revoke():
    img, d = new_slide()
    center_text(d, 150, "5  •  THE CONSEQUENCE", F_TAG, RED)
    center_text(d, 230, "MANDATE REVOKED", F_H1, WHITE)
    y = 400
    rows = [
        ("mandate-001", "revoked"),
        ("is_revoked", "true"),
        ("court effect", "revoke"),
    ]
    for label, val in rows:
        d.rounded_rectangle([90, y, W - 90, y + 108], radius=18, fill=CARD)
        d.text((130, y + 30), label, font=F_BODY, fill=MUTED)
        tw = d.textlength(val, font=F_BODY_B)
        d.text((W - 130 - tw, y + 30), val, font=F_BODY_B, fill=RED)
        y += 132
    y += 60
    y = wrap(d, 90, y, "The agent tries one more deal — the Delegation Manager blocks it.",
             F_BODY, WHITE, W - 180)
    y += 40
    d.rounded_rectangle([90, y, W - 90, y + 170], radius=24, fill=(74, 28, 28))
    center_text(d, y + 36, "deal-003  •  BLOCKED", F_H2, RED)
    center_text(d, y + 104, "FINISHED_WITH_ERROR", F_MONO, WHITE)
    y += 240
    y = tx_line(d, y, "blocked tx", TX_BLOCKED3)
    footer(d)
    img.save(FRAMES / "s6.png")


def slide7_outro():
    img, d = new_slide()
    center_text(d, 170, "Delegate & Defend", F_H1, WHITE)
    center_text(d, 270, "Every claim is a transaction.", F_BODY, MUTED)
    y = 420
    d.text((90, y), "Contract — DelegateCourt", font=F_BODY_B, fill=WHITE)
    y += 60
    d.text((90, y), CONTRACT[:34], font=F_MONO, fill=MONO)
    d.text((90, y + 42), CONTRACT[34:], font=F_MONO, fill=MONO)
    y += 130
    d.text((90, y), "explorer-studio-dev.genlayer.com", font=F_BODY, fill=MUTED)
    y += 60
    d.text((90, y), "GenLayer Studio Next  •  chain 61997", font=F_BODY, fill=MUTED)
    y += 120
    ic = logo_png("internet-court-logo", 480)
    gl = logo_png("genlayer-logo", 400)
    mm = logo_png("metamask-logo", 320)
    y = logo_card(img, ic, W // 2, y) + 40
    y = logo_card(img, gl, W // 2, y) + 40
    y = logo_card(img, mm, W // 2, y) + 60
    center_text(d, y, "Mission 101  •  Internet Court: Partner Demo Lab", F_TAG, BLUE)
    img.save(FRAMES / "s7.png")


if __name__ == "__main__":
    slide1_title()
    slide2_mandate()
    slide3_happy()
    slide4_dispute()
    slide5_verdict()
    slide6_revoke()
    slide7_outro()
    print("slides written to", FRAMES)
