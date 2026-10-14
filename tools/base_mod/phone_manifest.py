"""Add debuggable and optional icon label to a verified isolated PC manifest.

This permits app-own run-as provisioning on a non-rooted owner's phone. It
does not edit the publisher package, grant INTERNET or change game code.
"""
import struct
from tools.base_mod.binary_axml import string_values
from tools.base_mod.audit_offline_egress import manifest_components

PACKAGE='jp.kn.local.battlecats'
ANDROID_URI='http://schemas.android.com/apk/res/android'


def add_phone_debuggable(data: bytes, *, app_label: str | None = None) -> bytes:
    if len(data)<36 or struct.unpack_from('<HHI',data)!=(3,8,len(data)):
        raise ValueError('PHONE_MANIFEST_DOCUMENT_INVALID')
    values=string_values(data)
    if PACKAGE not in values:
        raise ValueError('PHONE_MANIFEST_PACKAGE_NOT_ISOLATED')
    if 'debuggable' in values:
        raise ValueError('PHONE_MANIFEST_DEBUG_ALREADY_PRESENT')
    if 'android.permission.INTERNET' in manifest_components(data)['declared_permissions']:
        raise ValueError('PHONE_MANIFEST_INTERNET_FORBIDDEN')
    kind,header,size,count,styles,flags,start,style_start=struct.unpack_from('<HHIIIIII',data,8)
    if kind!=1 or header!=28 or styles or style_start or start!=28+count*4:
        raise ValueError('PHONE_MANIFEST_STRING_POOL_UNSUPPORTED')
    if count!=len(values): raise ValueError('PHONE_MANIFEST_STRING_COUNT_INVALID')
    debug_index=count
    old_strings=data[8+start:8+size]
    words=['debuggable']+([app_label] if app_label is not None else [])
    encoded=bytearray(); new_offsets=[]
    for word in words:
        if not word or len(word)>40 or len(word.encode('utf-16le'))!=len(word)*2 or any(ord(c)<32 for c in word):
            raise ValueError('PHONE_MANIFEST_LABEL_INVALID')
        new_offsets.append(len(old_strings)+len(encoded))
        raw=word.encode('utf-8' if flags&0x100 else 'utf-16le')
        encoded.extend((bytes([len(word),len(raw)])+raw+b'\0' if flags&0x100 else
                       struct.pack('<H',len(word))+raw+b'\0\0'))
    encoded+=b'\0'*((-len(encoded))%4)
    added=len(words)*4
    pool=(struct.pack('<HHIIIIII',1,28,size+added+len(encoded),count+len(words),0,flags&~1,start+added,0)+
          data[36:8+start]+struct.pack('<'+'I'*len(words),*new_offsets)+old_strings+encoded)
    cursor=8+size
    if cursor+8>len(data): raise ValueError('PHONE_MANIFEST_RESOURCE_MAP_MISSING')
    kind,header,size=struct.unpack_from('<HHI',data,cursor)
    if kind!=0x180 or header!=8 or size<8 or (size-8)%4 or cursor+size>len(data):
        raise ValueError('PHONE_MANIFEST_RESOURCE_MAP_INVALID')
    resource=list(struct.unpack_from('<'+'I'*((size-8)//4),data,cursor+8))
    if len(resource)>count: raise ValueError('PHONE_MANIFEST_RESOURCE_MAP_TOO_LONG')
    resource+=([0]*(count-len(resource)))+[0x0101000f]+([0] if app_label is not None else [])
    output=[pool,struct.pack('<HHI',0x180,8,8+len(resource)*4)+struct.pack('<'+'I'*len(resource),*resource)]
    cursor+=size; matched=0; packages=[]; manifests=0
    namespace=values.index(ANDROID_URI)
    while cursor<len(data):
        if cursor+8>len(data): raise ValueError('PHONE_MANIFEST_CHUNK_INVALID')
        kind,header,size=struct.unpack_from('<HHI',data,cursor)
        if size<8 or cursor+size>len(data): raise ValueError('PHONE_MANIFEST_CHUNK_INVALID')
        chunk=bytearray(data[cursor:cursor+size])
        if kind==0x102 and size>=36:
            tag_index=struct.unpack_from('<I',chunk,20)[0]
            if tag_index>=count: raise ValueError('PHONE_MANIFEST_TAG_INDEX_INVALID')
            tag=values[tag_index]
            if tag=='manifest': manifests+=1
            attr_start,attr_size,attr_count=struct.unpack_from('<HHH',chunk,24)
            if header!=16 or attr_start!=20 or attr_size!=20 or size!=36+20*attr_count:
                raise ValueError('PHONE_MANIFEST_ELEMENT_LAYOUT_UNSUPPORTED')
            attrs=[bytes(chunk[36+i*20:56+i*20]) for i in range(attr_count)]
            for attr in attrs:
                ns,name,raw,value_size,reserved,kind_value,value=struct.unpack('<IIIHBBI',attr)
                if name>=count: raise ValueError('PHONE_MANIFEST_ATTRIBUTE_INDEX_INVALID')
                if tag=='manifest' and ns==0xffffffff and values[name]=='package':
                    if value_size!=8 or reserved or kind_value!=3 or value>=count or raw>=count or raw!=value:
                        raise ValueError('PHONE_MANIFEST_PACKAGE_VALUE_INVALID')
                    packages.append(values[value])
            if tag!='application':
                output.append(bytes(chunk)); cursor+=size; continue
            if app_label is not None:
                labels=[i for i,attr in enumerate(attrs) if struct.unpack_from('<II',attr)==(namespace,values.index('label'))]
                if len(labels)!=1: raise ValueError('PHONE_MANIFEST_LABEL_NOT_UNIQUE')
                attrs[labels[0]]=struct.pack('<IIIHBBI',namespace,values.index('label'),count+1,8,0,3,count+1)
            position=next((i for i,attr in enumerate(attrs)
                           if resource[struct.unpack_from('<I',attr,4)[0]]>0x0101000f),len(attrs))
            attrs.insert(position,struct.pack('<IIIHBBI',namespace,debug_index,0xffffffff,8,0,0x12,1))
            struct.pack_into('<I',chunk,4,size+20)
            struct.pack_into('<H',chunk,28,attr_count+1)
            for offset in (30,32,34):
                index=struct.unpack_from('<H',chunk,offset)[0]
                if index and index>position: struct.pack_into('<H',chunk,offset,index+1)
            chunk=chunk[:36]+b''.join(attrs)
            matched+=1
        output.append(bytes(chunk)); cursor+=size
    if matched!=1: raise ValueError('PHONE_MANIFEST_APPLICATION_NOT_UNIQUE')
    if manifests!=1 or packages!=[PACKAGE]: raise ValueError('PHONE_MANIFEST_PACKAGE_NOT_ISOLATED')
    body=b''.join(output)
    result=struct.pack('<HHI',3,8,len(body)+8)+body
    if string_values(result)!=values+words or manifest_components(result)!=manifest_components(data):
        raise ValueError('PHONE_MANIFEST_UNRELATED_COMPONENT_CHANGE')
    return result
