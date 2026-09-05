#!/usr/bin/env python3
"""
DuoPad - Brand Identity & Logo Generator
Procedurally renders an ultra-premium 3D standalone gamepad icon for DuoPad.
Features:
- Dual-color identity: Electric Cyan (Player 1) + Neon Magenta/Pink (Player 2)
- Central glowing stylized 'D' emblem
- 3D beveled metallic chassis with illuminated joysticks, lightbar, D-pad, and jewel action buttons
- Zero background frame (100% transparent alpha), tightly bounded to maximize icon size (~92% fill)
- Multi-resolution ICO (16x16 to 256x256) and master PNG assets (1024x1024, 512x512, 192x192)
"""

import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.interpolate import splprep, splev

def build_duopad_icon():
    W, H = 2048, 2048
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # -------------------------------------------------------------------------
    # 1. Ergonomic Gamepad Chassis Path
    # -------------------------------------------------------------------------
    control_points = [
        (1024, 530),   # Top center dip
        (1280, 500),   # Top right shoulder slope
        (1530, 520),   # Right shoulder bumper peak
        (1710, 670),   # Right upper corner
        (1820, 930),   # Right outer grip upper
        (1850, 1260),  # Right outer grip widest point
        (1770, 1580),  # Right outer grip lower taper
        (1610, 1800),  # Right grip bottom tip
        (1440, 1780),  # Right inner grip bottom
        (1340, 1500),  # Right inner thigh
        (1200, 1230),  # Right inner crotch
        (1024, 1190),  # Center bottom crotch arch
        (848, 1230),   # Left inner crotch
        (708, 1500),   # Left inner thigh
        (608, 1780),   # Left inner grip bottom
        (438, 1800),   # Left grip bottom tip
        (278, 1580),   # Left outer grip lower taper
        (198, 1260),   # Left outer grip widest point
        (228, 930),    # Left outer grip upper
        (338, 670),    # Left upper corner
        (518, 520),    # Left shoulder bumper peak
        (768, 500),    # Top left shoulder slope
    ]

    pts = np.array(control_points)
    pts_closed = np.vstack([pts, pts[0]])
    tck, u = splprep([pts_closed[:, 0], pts_closed[:, 1]], s=0, per=True)
    u_new = np.linspace(0, 1, 1200)
    x_new, y_new = splev(u_new, tck)
    smooth_poly = list(zip(x_new, y_new))

    # -------------------------------------------------------------------------
    # 2. Outer Dual Neon Glow (Cyan on Left, Magenta on Right)
    # -------------------------------------------------------------------------
    # Left Glow (Cyan #00f0ff)
    glow_left = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_gl = ImageDraw.Draw(glow_left)
    draw_gl.polygon(smooth_poly, fill=(0, 240, 255, 140))
    glow_left = glow_left.filter(ImageFilter.GaussianBlur(radius=80))

    # Right Glow (Magenta #ff007f)
    glow_right = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_gr = ImageDraw.Draw(glow_right)
    draw_gr.polygon(smooth_poly, fill=(255, 0, 140, 140))
    glow_right = glow_right.filter(ImageFilter.GaussianBlur(radius=80))

    # Mask Left half vs Right half for the ambient glow
    mask_grad = Image.new("L", (W, H), 0)
    m_arr = np.linspace(0, 255, W, dtype=np.uint8)
    mask_grad.paste(Image.fromarray(np.tile(m_arr, (H, 1))), (0, 0))

    # Composite dual glow
    glow_composite = Image.composite(glow_right, glow_left, mask_grad)
    img.alpha_composite(glow_composite)

    # -------------------------------------------------------------------------
    # 3. Gamepad Body Base & Gradient
    # -------------------------------------------------------------------------
    body_mask = Image.new("L", (W, H), 0)
    draw_bm = ImageDraw.Draw(body_mask)
    draw_bm.polygon(smooth_poly, fill=255)

    # Chassis metallic gradient: deep titanium/obsidian with subtle dual accent
    body_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_bl = ImageDraw.Draw(body_layer)

    y_grid, x_grid = np.mgrid[0:H, 0:W]
    # Center-normalized distance
    cx_norm = (x_grid - 1024) / 1024.0
    cy_norm = (y_grid - 1100) / 1000.0

    # Base dark carbon
    r_base = (16 + 18 * (cy_norm + 0.3) + np.clip(cx_norm, 0, 1) * 35).clip(12, 55).astype(np.uint8)
    g_base = (20 + 22 * (cy_norm + 0.3) + np.clip(-cx_norm, 0, 1) * 25).clip(14, 48).astype(np.uint8)
    b_base = (30 + 35 * (cy_norm + 0.3) + np.clip(-cx_norm, 0, 1) * 55 + np.clip(cx_norm, 0, 1) * 45).clip(22, 90).astype(np.uint8)
    a_base = np.full((H, W), 255, dtype=np.uint8)

    body_arr = np.dstack([r_base, g_base, b_base, a_base])
    body_img = Image.fromarray(body_arr, mode="RGBA")
    body_layer.paste(body_img, (0, 0), mask=body_mask)
    img.alpha_composite(body_layer)

    # -------------------------------------------------------------------------
    # 4. Beveled Inner Rim & Dual Grip Accents
    # -------------------------------------------------------------------------
    draw = ImageDraw.Draw(img)

    # Beveled rim
    draw.line(smooth_poly + [smooth_poly[0]], fill=(80, 110, 140, 180), width=8)

    # Left Grip Accent Stripe (Cyan)
    lg_pts = [
        (380, 750), (310, 950), (280, 1200), (320, 1450), (420, 1680)
    ]
    draw.line(lg_pts, fill=(0, 240, 255, 230), width=18, joint="curve")
    draw.line(lg_pts, fill=(255, 255, 255, 200), width=6, joint="curve")

    # Right Grip Accent Stripe (Magenta)
    rg_pts = [
        (1668, 750), (1738, 950), (1768, 1200), (1728, 1450), (1628, 1680)
    ]
    draw.line(rg_pts, fill=(255, 0, 140, 230), width=18, joint="curve")
    draw.line(rg_pts, fill=(255, 255, 255, 200), width=6, joint="curve")

    # -------------------------------------------------------------------------
    # 5. Top Lightbar (Cyan to Magenta Gradient Bridge)
    # -------------------------------------------------------------------------
    bar_w, bar_h = 440, 44
    bar_x, bar_y = 1024 - bar_w // 2, 540
    for i in range(bar_w):
        t = i / bar_w
        r = int((1 - t) * 0 + t * 255)
        g = int((1 - t) * 235 + t * 10)
        b = int((1 - t) * 255 + t * 160)
        draw.line([(bar_x + i, bar_y), (bar_x + i, bar_y + bar_h)], fill=(r, g, b, 230), width=1)
    # Lightbar glow overlay
    draw.rounded_rectangle([bar_x - 4, bar_y - 4, bar_x + bar_w + 4, bar_y + bar_h + 4], radius=22, outline=(255, 255, 255, 160), width=4)

    # -------------------------------------------------------------------------
    # 6. Left Thumbstick (Offset Upper-Left: 640, 930) - Player 1 Cyan Glow
    # -------------------------------------------------------------------------
    ls_x, ls_y, ls_r = 640, 930, 180
    # Outer bezel well
    draw.ellipse([ls_x - ls_r - 20, ls_y - ls_r - 20, ls_x + ls_r + 20, ls_y + ls_r + 20], fill=(12, 16, 24, 255), outline=(0, 240, 255, 180), width=8)
    # Stick cap shadow & base
    draw.ellipse([ls_x - ls_r, ls_y - ls_r, ls_x + ls_r, ls_y + ls_r], fill=(24, 30, 40, 255), outline=(50, 65, 85, 255), width=6)
    # Inner concave well
    draw.ellipse([ls_x - ls_r + 35, ls_y - ls_r + 35, ls_x + ls_r - 35, ls_y + ls_r - 35], fill=(16, 20, 28, 255), outline=(0, 240, 255, 220), width=6)
    # Grip textured rim dots
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        dx = int((ls_r - 18) * math.cos(rad))
        dy = int((ls_r - 18) * math.sin(rad))
        draw.ellipse([ls_x + dx - 6, ls_y + dy - 6, ls_x + dx + 6, ls_y + dy + 6], fill=(0, 240, 255, 220))

    # -------------------------------------------------------------------------
    # 7. D-Pad (Lower-Left: 790, 1260) - Beveled Cross
    # -------------------------------------------------------------------------
    dp_x, dp_y = 790, 1260
    arm_w, arm_l = 64, 150
    # Cross base well
    draw.rectangle([dp_x - arm_w // 2 - 10, dp_y - arm_l - 10, dp_x + arm_w // 2 + 10, dp_y + arm_l + 10], fill=(14, 18, 26, 255))
    draw.rectangle([dp_x - arm_l - 10, dp_y - arm_w // 2 - 10, dp_x + arm_l + 10, dp_y + arm_w // 2 + 10], fill=(14, 18, 26, 255))
    # Cross arms
    draw.rectangle([dp_x - arm_w // 2, dp_y - arm_l, dp_x + arm_w // 2, dp_y + arm_l], fill=(36, 44, 58, 255), outline=(70, 90, 120, 255), width=4)
    draw.rectangle([dp_x - arm_l, dp_y - arm_w // 2, dp_x + arm_l, dp_y + arm_w // 2], fill=(36, 44, 58, 255), outline=(70, 90, 120, 255), width=4)
    # Center indentation
    draw.ellipse([dp_x - 30, dp_y - 30, dp_x + 30, dp_y + 30], fill=(22, 28, 38, 255), outline=(0, 240, 255, 160), width=3)
    # Direction arrows
    draw.polygon([(dp_x, dp_y - arm_l + 18), (dp_x - 16, dp_y - arm_l + 42), (dp_x + 16, dp_y - arm_l + 42)], fill=(0, 240, 255, 230))
    draw.polygon([(dp_x, dp_y + arm_l - 18), (dp_x - 16, dp_y + arm_l - 42), (dp_x + 16, dp_y + arm_l - 42)], fill=(0, 240, 255, 230))
    draw.polygon([(dp_x - arm_l + 18, dp_y), (dp_x - arm_l + 42, dp_y - 16), (dp_x - arm_l + 42, dp_y + 16)], fill=(0, 240, 255, 230))
    draw.polygon([(dp_x + arm_l - 18, dp_y), (dp_x + arm_l - 42, dp_y - 16), (dp_x + arm_l - 42, dp_y + 16)], fill=(0, 240, 255, 230))

    # -------------------------------------------------------------------------
    # 8. Right Thumbstick (Offset Lower-Middle: 1258, 1260) - Player 2 Magenta Glow
    # -------------------------------------------------------------------------
    rs_x, rs_y, rs_r = 1258, 1260, 180
    # Outer bezel well
    draw.ellipse([rs_x - rs_r - 20, rs_y - rs_r - 20, rs_x + rs_r + 20, rs_y + rs_r + 20], fill=(12, 16, 24, 255), outline=(255, 0, 140, 180), width=8)
    # Stick cap
    draw.ellipse([rs_x - rs_r, rs_y - rs_r, rs_x + rs_r, rs_y + rs_r], fill=(24, 30, 40, 255), outline=(50, 65, 85, 255), width=6)
    # Inner concave well
    draw.ellipse([rs_x - rs_r + 35, rs_y - rs_r + 35, rs_x + rs_r - 35, rs_y + rs_r - 35], fill=(16, 20, 28, 255), outline=(255, 0, 140, 220), width=6)
    # Grip textured rim dots
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        dx = int((rs_r - 18) * math.cos(rad))
        dy = int((rs_r - 18) * math.sin(rad))
        draw.ellipse([rs_x + dx - 6, rs_y + dy - 6, rs_x + dx + 6, rs_y + dy + 6], fill=(255, 0, 140, 220))

    # -------------------------------------------------------------------------
    # 9. Action Buttons Diamond (Upper-Right: 1408, 930) - Y, B, A, X Jewel Style
    # -------------------------------------------------------------------------
    ab_x, ab_y = 1408, 930
    btn_offset = 125
    btn_r = 52

    buttons = [
        ("Y", ab_x, ab_y - btn_offset, (255, 215, 0)),    # Top: Yellow Y
        ("B", ab_x + btn_offset, ab_y, (255, 50, 80)),    # Right: Red B
        ("A", ab_x, ab_y + btn_offset, (0, 240, 120)),    # Bottom: Green A
        ("X", ab_x - btn_offset, ab_y, (0, 190, 255)),    # Left: Blue X
    ]

    for label, bx, by, col in buttons:
        # Button socket well
        draw.ellipse([bx - btn_r - 8, by - btn_r - 8, bx + btn_r + 8, by + btn_r + 8], fill=(12, 16, 24, 255), outline=(40, 50, 68, 255), width=4)
        # Button 3D dome
        draw.ellipse([bx - btn_r, by - btn_r, bx + btn_r, by + btn_r], fill=(24, 30, 42, 255), outline=col, width=6)
        # Inner gloss highlight
        draw.ellipse([bx - btn_r + 14, by - btn_r + 10, bx + btn_r - 14, by - 6], fill=(255, 255, 255, 80))
        # Letter label approximation / jewel core
        draw.ellipse([bx - 18, by - 18, bx + 18, by + 18], fill=col)

    # -------------------------------------------------------------------------
    # 10. Center Duo Nexus Emblem: Stylized Glowing "DUO" Crest
    # -------------------------------------------------------------------------
    cen_x, cen_y = 1024, 880
    cen_r = 110
    # Outer glowing nexus ring
    draw.ellipse([cen_x - cen_r - 16, cen_y - cen_r - 16, cen_x + cen_r + 16, cen_y + cen_r + 16], fill=(10, 14, 20, 255))
    draw.ellipse([cen_x - cen_r, cen_y - cen_r, cen_x + cen_r, cen_y + cen_r], fill=(18, 24, 36, 255), outline=(70, 90, 120, 255), width=5)

    # Stylized Glowing "D" Symbol in Nexus
    # Left vertical stem of D (Cyan glow)
    draw.rounded_rectangle([cen_x - 55, cen_y - 65, cen_x - 25, cen_y + 65], radius=8, fill=(0, 240, 255, 255))
    # Right curved arc of D (Magenta glow)
    draw.arc([cen_x - 55, cen_y - 65, cen_x + 65, cen_y + 65], start=-90, end=90, fill=(255, 0, 140, 255), width=30)
    # Inner bright core
    draw.ellipse([cen_x - 12, cen_y - 12, cen_x + 12, cen_y + 12], fill=(255, 255, 255, 240))

    # Center Nav buttons (View / Menu)
    draw.rounded_rectangle([860, 770, 930, 810], radius=12, fill=(30, 40, 56, 255), outline=(0, 240, 255, 180), width=3)
    draw.rounded_rectangle([1118, 770, 1188, 810], radius=12, fill=(30, 40, 56, 255), outline=(255, 0, 140, 180), width=3)

    # -------------------------------------------------------------------------
    # 11. Bounding Box Crop & Tight Fit (~92% canvas fill)
    # -------------------------------------------------------------------------
    bbox = img.getbbox()
    cropped = img.crop(bbox)
    cw, ch = cropped.size

    # Target: 512x512 canvas with ~92% width fill (470px width)
    target_canvas = 512
    target_w = 472
    target_h = int(ch * (target_w / cw))

    # Resize with ultra-smooth Lanczos downsampling
    resized = cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)

    final_512 = Image.new("RGBA", (target_canvas, target_canvas), (0, 0, 0, 0))
    offset_x = (target_canvas - target_w) // 2
    offset_y = (target_canvas - target_h) // 2
    final_512.paste(resized, (offset_x, offset_y), mask=resized)

    # Save outputs
    out_dir = os.path.dirname(os.path.abspath(__file__))
    p_png512 = os.path.join(out_dir, "duopad_icon.png")
    p_ico = os.path.join(out_dir, "duopad_icon.ico")
    p_pwa192 = os.path.join(out_dir, "static", "icon-192.png")
    p_pwa512 = os.path.join(out_dir, "static", "icon-512.png")

    final_512.save(p_png512, "PNG")

    # Multi-resolution ICO
    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    final_512.save(p_ico, format="ICO", sizes=ico_sizes)

    # PWA Mobile Icons
    final_192 = final_512.resize((192, 192), Image.Resampling.LANCZOS)
    final_192.save(p_pwa192, "PNG")
    final_512.save(p_pwa512, "PNG")

    # Also save a copy to the brain artifact directory for inspection
    brain_dir = r"C:\Users\mo.mastur\.gemini\antigravity-ide\brain\c28e4260-5504-48ed-aa37-53f0cef30920"
    if os.path.exists(brain_dir):
        final_512.save(os.path.join(brain_dir, "duopad_standalone_logo.png"), "PNG")

    print(f"[+] DuoPad Brand Logo generated successfully:")
    print(f"    PNG: {p_png512}")
    print(f"    ICO: {p_ico}")
    print(f"    PWA: {p_pwa192}, {p_pwa512}")

if __name__ == "__main__":
    build_duopad_icon()
