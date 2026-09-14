"""Bounded reader for the pinned Darwin x8664 bootstrap's read-only section."""
from collections import Counter
import struct
from common import require

PAGE=4096
FUNCTION=149  # x8664 (9 << 4) | fulltag-nodeheader-0
# Only object classes actually present in this bootstrap's read-only section.
# Other legitimate CCL image classes are deliberately outside this reader.
WIDTHS={201:4,183:2,233:4,231:1,41:4,25:4,149:8,167:2,217:4}
SIG=(0x4f70656e,0x4d434c49,0x6d616765,0x46696c65)
def page(n):return (n+PAGE-1)&-PAGE


def parse(blob):
    require(len(blob)>=80,'IMAGE_LENGTH')
    trailer=struct.unpack_from('<IIIi',blob,len(blob)-16)
    require(trailer[:3]==SIG[:3] and trailer[3]<0,'IMAGE_TRAILER')
    offset=len(blob)+trailer[3]
    require(0<=offset<=len(blob)-80,'IMAGE_HEADER_OFFSET')
    h=struct.unpack_from('<12I2Q',blob,offset)
    require(h[:4]==SIG and h[7]==5 and h[8]==1042 and h[11]==83,'IMAGE_HEADER_PROFILE')
    require(h[12]==h[13] and h[12]==0x300000000000,'IMAGE_BASE_PROFILE')
    require(offset+64+5*32==len(blob)-16,'IMAGE_HEADER_EXTENT')
    high=h[9] if h[9]<2**31 else h[9]-2**32
    position=offset+64+5*32+(high<<32)+h[10]
    require(position==0,'IMAGE_DATA_OFFSET')
    sections=[]
    for i,code in enumerate((64,32,72,56,48)):
        row=struct.unpack_from('<4Q',blob,offset+64+32*i)
        require(row[0]==code and row[1]==0 and row[2]%16==0,'IMAGE_SECTION_PROFILE')
        position=page(position);size=row[2]
        require(position+size<=offset,'IMAGE_SECTION_EXTENT')
        sections.append(dict(code=code,offset=position,bytes=size,static_dnodes=row[3]))
        position+=size
        if code==56 and size:
            position=page(position)+page(((size>>4)+7)>>3)
    require(position==offset,'IMAGE_DATA_EXTENT')
    section=sections[1];position=section['offset'];end=position+section['bytes']
    functions=[];counts=Counter()
    while position<end:
        header=struct.unpack_from('<Q',blob,position)[0];subtag=header&255;count=header>>8
        require(subtag in WIDTHS or subtag==247,'READONLY_HEADER')
        payload=(count+7)//8 if subtag==247 else count*WIDTHS[subtag]
        size=(8+payload+15)&-16
        require(size>0 and position+size<=end,'READONLY_OBJECT_EXTENT')
        counts[str(subtag)]+=1
        if subtag==FUNCTION:
            require(count>=2,'FUNCTION_WORD_COUNT')
            code_words=struct.unpack_from('<I',blob,position+8)[0]
            require(0<code_words<=count-2,'FUNCTION_CODE_BOUNDARY')
            functions.append(dict(file_offset=position,section_offset=position-section['offset'],
                                  total_words=count,code_words=code_words,object_bytes=size))
        position+=size
    require(position==end,'READONLY_WALK_END')
    # INVENTORY pushes while %MAP-LFUNS walks; its recorded order is reversed.
    return dict(header_offset=offset,sections=sections,readonly_object_counts=dict(counts),
                functions=list(reversed(functions)))

