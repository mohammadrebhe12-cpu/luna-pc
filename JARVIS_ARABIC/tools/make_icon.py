"""يولّد assets/icon.png و icon.ico (تشغيل مرة واحدة)."""
import math
from PIL import Image, ImageDraw
S = 512
im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
d.ellipse((8, 8, S-8, S-8), fill=(10, 6, 20, 255), outline=(179, 136, 255, 255), width=14)
for i in range(72):
    a = math.radians(i*5); r1, r2 = 228, 205 if i % 6 == 0 else 216
    d.line((S/2+r1*math.cos(a), S/2+r1*math.sin(a), S/2+r2*math.cos(a), S/2+r2*math.sin(a)), fill=(179, 136, 255, 200), width=4)
d.arc((90, 90, S-90, S-90), 200, 320, fill=(124, 77, 255, 255), width=14)
d.arc((90, 90, S-90, S-90), 20, 140, fill=(124, 77, 255, 255), width=14)
for r, a in [(80, 255), (110, 120), (140, 50)]:
    d.ellipse((S/2-r, S/2-r, S/2+r, S/2+r), fill=(179, 136, 255, a) if r == 80 else None, outline=None if r == 80 else (179, 136, 255, a), width=6)
d.ellipse((S/2-40, S/2-40, S/2+40, S/2+40), fill=(255, 255, 255, 255))
im.save("assets/icon.png")
im.save("assets/icon.ico", sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
