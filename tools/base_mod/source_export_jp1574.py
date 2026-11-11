"""Exact APK-only JP15.7.4 export captured from the owner device.

All six publisher signatures matched the owned JP15.7.1 source. No APK,
player data or credentials are contained here. Legacy source pins stay separate.
"""
from pathlib import Path
from zipfile import ZipFile
import io

EXPORT_SHA256 = 'e091248a1770c901c727699dac60410279eca32580047c816f49c15cd3f294c3'
SPLITS = {'base.apk': {'sha256': 'aefc6bcdf780e054907cc9fceeda6181337eeb7c81794291679af58428febc04',
              'size': 25918020},
 'split_InstallPack.apk': {'sha256': 'e688034e6f04b093a385c988830c19b375eb6d1833f3af38ef832f51b7f077c0',
                           'size': 132290560},
 'split_config.arm64_v8a.apk': {'sha256': '5f060e7423cdb4550d9e64e217ae0afae3d5a0a67563115e6b9b2f0fd5fe058c',
                                'size': 15385466},
 'split_config.en.apk': {'sha256': '091b04e8ff826a818b913b811f2899a04e2242206da961be336bcc71e78f1552',
                         'size': 49362},
 'split_config.ja.apk': {'sha256': '08de29b372003c9b45508b53e90bccdc1c8ad1b9ebed4f7d320d88499bb73d8a',
                         'size': 24786},
 'split_config.xxhdpi.apk': {'sha256': '6262e4a0a1907970b1efb96f9b2286e121e8cfe7c6bb7a54693a33d180bb5b86',
                             'size': 231726}}


def verify_legacy_asset_equivalence(owner_export: Path, asset_export: Path):
    """Allow legacy asset converters only when every InstallPack asset matches."""
    with ZipFile(owner_export) as current, ZipFile(asset_export) as legacy:
        def pack(archive):
            names=[n for n in archive.namelist() if Path(n).name=='split_InstallPack.apk']
            if len(names)!=1:raise ValueError('SOURCE_INSTALLPACK_AMBIGUOUS')
            return ZipFile(io.BytesIO(archive.read(names[0])))
        with pack(current) as new, pack(legacy) as old:
            names=set(old.namelist())-{'AndroidManifest.xml'}
            names={n for n in names if not n.startswith('META-INF/')}
            new_names={n for n in new.namelist() if n!='AndroidManifest.xml' and not n.startswith('META-INF/')}
            if names!=new_names or any(old.read(n)!=new.read(n) for n in names):
                raise ValueError('JP1574_LEGACY_ASSETS_CHANGED')
    return dict(legacy_asset_conversion_source='jp1571',all_installpack_assets_identical=True)
