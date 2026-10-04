#!/usr/bin/env python3
"""把一组静帧拼成联系表，方便一次看完。python3 tools/sheet.py out.jpg cols w a.jpg b.jpg ..."""
import sys
from PIL import Image, ImageDraw
out, cols, w = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); fs = sys.argv[4:]
h = int(w * 16 / 9); rows = (len(fs) + cols - 1) // cols
s = Image.new('RGB', (w * cols, h * rows), 'gray')
for i, f in enumerate(fs):
    im = Image.open(f).resize((w, h)); d = ImageDraw.Draw(im); d.rectangle([0, 0, 76, 22], fill='black'); d.text((4, 5), f.split('_')[-1][:-4] + 's', fill='yellow')
    s.paste(im, ((i % cols) * w, (i // cols) * h))
s.save(out, quality=85)
