from odf.opendocument import load
from odf.element import Element
from odf.text import P, H, Span, List, ListItem, Note
from odf import text, teletype
from io import BytesIO
from urllib.request import urlopen
import requests

def _has_note_ancestor(elem):
    """Check if an element is nested inside a footnote/endnote body."""
    node = elem.parentNode
    while node is not None:
        if getattr(node, 'qname', (None, None))[1] == 'note':
            return True
        node = getattr(node, 'parentNode', None)
    return False

def _extract_text_without_notes(elem):
    """Extract text from an element, skipping any inline note (footnote/endnote) content."""
    if getattr(elem, 'qname', (None, None))[1] == 'note':
        return ''
    if hasattr(elem, 'data'):
        return elem.data
    return ''.join(_extract_text_without_notes(child) for child in elem.childNodes)

def readtext(url, include_footnotes=False):
    response = requests.get(url, timeout=30)
    doc = load(BytesIO(response.content))

    Elements = \
        doc.text.getElementsByType(P) +  \
        doc.text.getElementsByType(H)

    paragraphs = []
    for elem in Elements:
        if not include_footnotes and _has_note_ancestor(elem):
            continue
        if include_footnotes:
            paragraphs.append(teletype.extractText(elem))
        else:
            paragraphs.append(_extract_text_without_notes(elem))

    return "\n".join(paragraphs)


 ## --------- READ IN NEW BC DOCUMENTS
bctext = {}
for x,y in enumerate(bc['link']):
    try:
        thetext = readtext(y)
    except:
        thetext = 'link_broken'
    bctext[x] = thetext
bc['TEXT']  = list(bctext.values())


## --------- READ IN NEW ADDENDUM DOCUMENTS
addtext = {}
for x,y in enumerate(add['link']):
    try:
        thetext = readtext(y)
    except:
        thetext = 'link_broken'
    addtext[x] = thetext
add['TEXT']  = list(addtext.values())

