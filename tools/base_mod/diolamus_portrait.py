"""Import the owner's exact illustration into Diolamus (No.178) fourth-form atlases.

Art stays private. Only the native image interiors change: atlas sizes, frame, level
plaque and transparent padding are retained, mirroring the Godzilla first-form swap.
The battle sprite atlas is not touched.
"""
import hashlib
import io
from pathlib import Path

from tools.battlecats_pack import PackReader

SOURCE_SHA256 = '61a16505aba90bdafb69bd07df7f7bc24773f1bf9c201422079fb9a03c2dff8d'
SOURCE_SIZE = (783, 514)
ORIGINALS = {
    'uni177_u00.png': ('RUnitServer', (128, 128), '11c1d8da16b541a7878817904b31779f1aa425c97fd0fbe45891482d83f54779'),
    'udi177_u.png': ('RUnitServer', (512, 128), 'ef754fce768abf1ae640ff3005684086e918dd21551ad3802d0ef63129de1472'),
}
PORTRAIT_SHA256 = {
    'uni177_u00.png': '1280904b2b355d869e810c82fd5b9760396b7501e45668924c214a100bc6e910',
    'udi177_u.png': 'bf1411222e53782008f675615b61ab0f22a3a03660fe9d4637b98b4615e997ab',
}


def prepare_portraits(source: Path, server: Path) -> dict[str, bytes]:
    raw = source.read_bytes()
    if source.is_symlink() or hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('PC_DIOLAMUS_PORTRAIT_SOURCE_CHANGED')
    from PIL import Image, ImageDraw, ImageOps

    with Image.open(io.BytesIO(raw)) as source_image:
        if source_image.format != 'PNG' or source_image.size != SOURCE_SIZE:
            raise ValueError('PC_DIOLAMUS_PORTRAIT_SOURCE_FORMAT_CHANGED')
        art = source_image.convert('RGBA')
    packs = {}
    result = {}
    for name, (family, size, digest) in ORIGINALS.items():
        if family not in packs:
            packs[family] = PackReader(family, (server / (family + '.list')).read_bytes(),
                                      (server / (family + '.pack')).read_bytes(), region='jp')
        original = packs[family].read(name)[0]
        if hashlib.sha256(original).hexdigest() != digest:
            raise ValueError('PC_DIOLAMUS_PORTRAIT_ORIGINAL_CHANGED')
        with Image.open(io.BytesIO(original)) as image:
            if image.format != 'PNG' or image.size != size:
                raise ValueError('PC_DIOLAMUS_PORTRAIT_ATLAS_CHANGED')
            atlas = image.convert('RGBA')
        if name.startswith('uni'):
            atlas.paste(ImageOps.fit(art, (100, 74), method=Image.Resampling.LANCZOS), (14, 26))
        else:
            # Retain the original lower-right level plaque and surrounding frame.
            mask = Image.new('L', size)
            ImageDraw.Draw(mask).polygon([(15, 3), (309, 3), (309, 68), (189, 68),
                                          (146, 110), (15, 110)], fill=255)
            layer = Image.new('RGBA', size)
            layer.paste(ImageOps.fit(art, (295, 108), method=Image.Resampling.LANCZOS), (15, 3))
            atlas.paste(layer, (0, 0), mask)
        out = io.BytesIO()
        atlas.save(out, format='PNG', compress_level=9)
        payload = out.getvalue()
        if hashlib.sha256(payload).hexdigest() != PORTRAIT_SHA256[name]:
            raise ValueError('PC_DIOLAMUS_PORTRAIT_OUTPUT_CHANGED')
        result[name] = payload
    return result
