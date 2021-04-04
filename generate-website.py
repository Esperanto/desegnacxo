#!/usr/bin/python3

import gi

gi.require_version('Rsvg', '2.0')
from gi.repository import Rsvg
gi.require_version('Pango', '1.0')
from gi.repository import Pango
gi.require_version('PangoCairo', '1.0')
from gi.repository import PangoCairo

import os
import html
import cairo
import collections
import sys
import glob
import re
from PIL import Image
import PIL.ImageOps
import shutil
import hashlib

DRAWING_SIZE = (450, 470)
TITLE_HEIGHT = 52
IMAGE_SIZE = (DRAWING_SIZE[0], DRAWING_SIZE[1] + TITLE_HEIGHT)            

HTML_HEADER = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" type="text/css" href="desegnacxo.css">
<title>Desegnaĉo – {}</title>
<script src="desegnacxo.js"></script>
</head>
<body>
"""

HTML_FOOTER = """\
</body>
</html>"""

CARD_TEMPLATE = HTML_HEADER + """\
<img src="{:03d}.png">
<ol>
{}
</ol>
<div class="navigation">
{}
</div>
""" + HTML_FOOTER

IMAGE_EXTENSIONS = ['svg', 'jpeg', 'jpg']

def fit_size(w, h):
    if w / h > DRAWING_SIZE[0] / DRAWING_SIZE[1]:
        out_w = DRAWING_SIZE[0]
        out_h = h * out_w // w
    else:
        out_h = DRAWING_SIZE[1]
        out_w = w * out_h // h

    return out_w, out_h

def apply_orientation(im, orientation):
    if orientation == 1:
        return im
    elif orientation == 3:
        rotation = 180
    elif orientation == 6:
        rotation = 90
    elif orientation == 8:
        rotation = 270
    else:
        raise Exception("Unknown orientation {}".format(orientation))

    return im.rotate(360 - rotation, expand=True)

class Card(collections.namedtuple('Card', ['title', 'features'])):
    def _load_svg(self, cr, image_fn):
        svg = Rsvg.Handle.new_from_file(image_fn)
        dim = svg.get_dimensions()
        w, h = fit_size(dim.width, dim.height)
        scale = w / dim.width

        cr.save()
        cr.translate(DRAWING_SIZE[0] / 2 - w / 2,
                     DRAWING_SIZE[1] / 2 - h / 2)
        cr.scale(scale, scale)
        svg.render_cairo(cr)
        cr.restore()        

    def _load_image(self, cr, image_fn):
        with Image.open(image_fn) as im:
            exif = im.getexif()
            if 274 in exif:
                im = apply_orientation(im, exif[274])
            w, h = fit_size(im.width, im.height)
            scaled_im = im.resize((w, h))

        if 'A' not in scaled_im.getbands():
            scaled_im.putalpha(255)

        arr = bytearray(scaled_im.tobytes('raw', 'BGRa'))
        surface = cairo.ImageSurface.create_for_data(arr,
                                                     cairo.FORMAT_RGB24,
                                                     w,
                                                     h)
        pattern = cairo.SurfacePattern(surface)
        m = cairo.Matrix()
        m.translate(w // 2 - DRAWING_SIZE[0] // 2,
                    h // 2 - DRAWING_SIZE[1] // 2)
        pattern.set_matrix(m)

        cr.save()
        cr.set_source(pattern)
        cr.paint()
        cr.restore()

    def generate_image(self, image_fn, card_num):
        surface = cairo.ImageSurface(cairo.FORMAT_RGB24, *IMAGE_SIZE)
        cr = cairo.Context(surface)

        cr.save()
        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        cr.paint()
        cr.restore()

        if image_fn.endswith('.svg'):
            self._load_svg(cr, image_fn)
        else:
            self._load_image(cr, image_fn)

        cr.rectangle(0, DRAWING_SIZE[1], DRAWING_SIZE[0], TITLE_HEIGHT)
        cr.set_source_rgb(0.81, 0.89, 0.62)
        cr.fill()

        cr.set_source_rgb(0, 0, 0)

        fd = Pango.FontDescription("Sans")
        fd.set_absolute_size(TITLE_HEIGHT * 0.5 * Pango.SCALE)
        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(fd)
        layout.set_text(self.title, -1)
        (ink_rect, logical_rect) = layout.get_pixel_extents()
        cr.move_to(DRAWING_SIZE[0] / 2 - logical_rect.width / 2,
                   DRAWING_SIZE[1] + TITLE_HEIGHT * 0.2)
        PangoCairo.show_layout(cr, layout)

        surface.write_to_png("retejo/{:03d}.png".format(card_num))

def generate_index(f, cards):
    print(HTML_HEADER.format("Indekso") + "<ul>", file=f)
    for card_num, card in enumerate(cards):
        print("<li>{:03d}. <a href=\"{:03d}.html\">{}</a>".
              format(card_num, card_num, html.escape(card.title)),
              file=f)
    print("</ul>\n" + HTML_FOOTER, file=f)

def load_card(fn):
    features = []
    title = None

    with open(fn, 'rt', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            if len(line) == 0:
                if len(features) == 1 and title is None:
                    title = features[0]
                    features.clear()
                continue

            md = re.match(r'[0-9]+\. *(.*)', line)
            if md:
                line = md.group(1)

            features.append(line)

    if title is None:
        title = os.path.splitext(os.path.basename(fn))[0]

    return Card(title, features)

def find_image(fn):
    base = os.path.splitext(fn)[0]

    for ext in IMAGE_EXTENSIONS:
        image_fn = '{}.{}'.format(base, ext)
        if os.path.exists(image_fn):
            return image_fn

    return None

try:
    os.mkdir('retejo')
except FileExistsError:
    pass

cards = []

for fn in glob.glob('desegnajxoj/*.txt'):
    image_fn = find_image(fn)

    if image_fn is None:
        print("Missing title for “{}”".format(fn), file=sys.stderr)
        continue

    card = load_card(fn)
    card.generate_image(image_fn, len(cards))
    cards.append(card)

# Sort the cards in a consistent but unpredictable order so that
# stepping through them one by one seems random but the order will
# always be the same between invocations of the script
cards.sort(key=lambda c: hashlib.sha256(c.title.encode('utf-8')).digest())

for card_num, card in enumerate(cards):
    with open("retejo/{:03d}.html".format(card_num),
              'wt', encoding='utf-8') as f:
        if len(card.features) != 10:
            print("warning: the card “{:03d}: {:s}” "
                  "has {:d} features in {:s}".
                  format(card_num, card.title,
                         len(card.features),
                         language),
                  file=sys.stderr)
        feature_list = "\n".join("<li>{}".format(html.escape(feature))
                                 for feature in card.features)
        navigation = []
        if card_num > 0:
            navigation.append("<a href=\"{:03d}.html\">🠜</a>".
                              format(card_num - 1))
        navigation.append("<a href=\"index.html\">🏠</a>")
        if card_num + 1 < len(cards):
            navigation.append("<a href=\"{:03d}.html\">🠊</a>".
                              format(card_num + 1))
        print(CARD_TEMPLATE.format(card.title,
                                   card_num,
                                   feature_list,
                                   " | ".join(navigation)),
              file=f)

with open("retejo/index.html", 'wt', encoding='utf-8') as f:
    generate_index(f, cards)

for fn in ["desegnacxo.js", "desegnacxo.css"]:
    shutil.copy(fn, "retejo")
