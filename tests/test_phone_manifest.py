import struct
import unittest
from tools.base_mod.phone_manifest import add_phone_debuggable
from tools.base_mod.binary_axml import string_values


def fixture(utf8=False,package='jp.kn.local.battlecats'):
    values=['application','http://schemas.android.com/apk/res/android','label',
            package,'manifest','package']
    strings=bytearray(); offsets=[]
    for value in values:
        offsets.append(len(strings)); raw=value.encode('utf-8' if utf8 else 'utf-16le')
        strings.extend((bytes([len(value),len(raw)]) if utf8 else struct.pack('<H',len(value)))+raw+(b'\0' if utf8 else b'\0\0'))
    strings.extend(b'\0'*((-len(strings))%4))
    pool=struct.pack('<HHIIIIII',1,28,28+24+len(strings),6,0,0x100 if utf8 else 0,52,0)
    pool+=struct.pack('<6I',*offsets)+strings
    resource=struct.pack('<HHI6I',0x180,8,32,0,0,0x01010001,0,0,0)
    def start(name,ns,attr,value):
        return (struct.pack('<HHIII',0x102,16,56,1,0xffffffff)+
                struct.pack('<II6H',0xffffffff,name,20,20,1,0,0,0)+
                struct.pack('<IIIHBBI',ns,attr,value,8,0,3,value))
    body=pool+resource+start(4,0xffffffff,5,3)+start(0,1,2,2)
    return struct.pack('<HHI',3,8,8+len(body))+body


class PhoneManifestTests(unittest.TestCase):
    def test_only_adds_debug_attribute_and_preserves_original_string_indices(self):
        for utf8 in (False,True):
            original=fixture(utf8)
            result=add_phone_debuggable(original)
            self.assertEqual(string_values(result)[:-1],string_values(original))
            self.assertEqual(string_values(result)[-1],'debuggable')
            self.assertEqual(struct.unpack_from('<I',result,4)[0],len(result))
            self.assertIn(struct.pack('<I',0x0101000f),result)
            with self.assertRaisesRegex(ValueError,'ALREADY_PRESENT'): add_phone_debuggable(result)

    def test_rejects_foreign_package_and_truncated_document(self):
        with self.assertRaisesRegex(ValueError,'PACKAGE'): add_phone_debuggable(fixture(package='jp.co.ponos.battlecats'))
        with self.assertRaises(ValueError): add_phone_debuggable(fixture()[:-1])

    def test_rejects_unused_isolated_name_with_foreign_actual_package(self):
        data=bytearray(fixture())
        first=len(data)-112
        struct.pack_into('<I',data,first+44,2)
        struct.pack_into('<I',data,first+52,2)
        with self.assertRaisesRegex(ValueError,'PACKAGE_NOT_ISOLATED'): add_phone_debuggable(bytes(data))

    def test_can_distinguish_phone_icon_without_changing_other_components(self):
        original=fixture(True)
        result=add_phone_debuggable(original,app_label='にーくらホワイトにゃんこ')
        self.assertEqual(string_values(result),string_values(original)+['debuggable','にーくらホワイトにゃんこ'])

    def test_rejects_package_raw_and_typed_disagreement(self):
        data=bytearray(fixture())
        struct.pack_into('<I',data,len(data)-112+44,2)
        with self.assertRaisesRegex(ValueError,'PACKAGE_VALUE_INVALID'): add_phone_debuggable(bytes(data))
