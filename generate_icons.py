"""Generate PWA icons from source image at multiple sizes."""
import os
from PIL import Image

SRC = r"C:\Users\pc\.gemini\antigravity\brain\6e1ebb52-a38b-4c2d-9f86-15f1dd0b1b82\nutritrack_icon_1778763054155.png"
OUT = r"c:\Users\pc\OneDrive\Desktop\nutritrack\icons"

SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

os.makedirs(OUT, exist_ok=True)
img = Image.open(SRC).convert('RGBA')

for s in SIZES:
    resized = img.resize((s, s), Image.LANCZOS)
    resized.save(os.path.join(OUT, f'icon-{s}.png'), 'PNG')
    print(f"  ✅ icon-{s}.png")

print("\nAll icons generated!")
