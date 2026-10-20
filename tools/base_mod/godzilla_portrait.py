"""Import the owner's exact illustration into three original first-form atlases.

Art remains private. Only native image interiors change; atlas sizes, frame,
level plaque and transparent padding are retained. No battle texture is edited.
"""
import hashlib
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from tools.battlecats_pack import PackReader

SOURCE_SHA256 = '1bf03b97a7bd0327990101dcfdc112850d37cb51960f3f277b1faaea94a2af65'
ORIGINALS = {
    'uni702_f00.png': ('QUnitServer', (128, 128), '156d1bb45b9e262c6574ef0548df92a1319ad540d0ab63990a11f4584617c177'),
    'udi702_f.png': ('QUnitServer', (512, 128), '38571b3b4113d1b9ea75cd76e0297d931853d3cb8fdab64c653947940dc24614'),
    'gatyachara_702_f.png': ('QImageServer', (128, 128), 'cc1fd00b9da34ace06f9a6856f44fc01e06926eb3d1ea8e9341528e06cdadb3f'),
}
PORTRAIT_SHA256 = {
    'uni702_f00.png': 'eb4b242cd2222b2bc8fed82d3cea5633c1874c9882eeb4265e2d05b5ad11f5ef',
    'udi702_f.png': '55ae3a0f93bc830fc0a8529714bd675e77cd59e34440f0a97d181132e7af88ce',
    'gatyachara_702_f.png': '89c4dcbc25811fa9b8e97a3cccba62810f57b5d1c53c1e78690a5dc9eabf3132',
}


def prepare_portraits(source: Path, server: Path) -> dict[str, bytes]:
    raw = source.read_bytes()
    if source.is_symlink() or hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('PC_GODZILLA_PORTRAIT_SOURCE_CHANGED')
    with Image.open(io.BytesIO(raw)) as source_image:
        if source_image.format != 'PNG' or source_image.size != (575, 402):
            raise ValueError('PC_GODZILLA_PORTRAIT_SOURCE_FORMAT_CHANGED')
        art = source_image.convert('RGBA')
    packs = {}
    result = {}
    for name, (family, size, digest) in ORIGINALS.items():
        if family not in packs:
            packs[family] = PackReader(family, (server / (family + '.list')).read_bytes(),
                                      (server / (family + '.pack')).read_bytes(), region='jp')
        original = packs[family].read(name)[0]
        if hashlib.sha256(original).hexdigest() != digest:
            raise ValueError('PC_GODZILLA_PORTRAIT_ORIGINAL_CHANGED')
        with Image.open(io.BytesIO(original)) as image:
            if image.format != 'PNG' or image.size != size:
                raise ValueError('PC_GODZILLA_PORTRAIT_ATLAS_CHANGED')
            atlas = image.convert('RGBA')
        if name.startswith('uni'):
            atlas.paste(ImageOps.fit(art, (100, 74), method=Image.Resampling.LANCZOS), (14, 26))
        elif name.startswith('udi'):
            # Retain the original lower-right level plaque and surrounding frame.
            mask = Image.new('L', size)
            ImageDraw.Draw(mask).polygon([(15, 3), (309, 3), (309, 68), (189, 68),
                                          (146, 110), (15, 110)], fill=255)
            layer = Image.new('RGBA', size)
            layer.paste(ImageOps.fit(art, (295, 108), method=Image.Resampling.LANCZOS), (15, 3))
            atlas.paste(layer, (0, 0), mask)
        else:
            atlas.paste(ImageOps.fit(art, (126, 126), method=Image.Resampling.LANCZOS,
                                     centering=(.8, .5)), (1, 1))
        output = io.BytesIO()
        atlas.save(output, format='PNG', compress_level=9)
        payload = output.getvalue()
        if hashlib.sha256(payload).hexdigest() != PORTRAIT_SHA256[name]:
            raise ValueError('PC_GODZILLA_PORTRAIT_OUTPUT_CHANGED')
        result[name] = payload
    return result
