import os
import pickle
import requests
from odf.opendocument import load
from odf.text import P, H
from odf import teletype
from io import BytesIO

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(SCRIPT_DIR, 'doc_links.pkl'), 'rb') as f:
    data = pickle.load(f)
bc  = data['bc']
add = data['add']


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
    elements = doc.text.getElementsByType(P) + doc.text.getElementsByType(H)
    paragraphs = []
    for elem in elements:
        if not include_footnotes and _has_note_ancestor(elem):
            continue
        if include_footnotes:
            paragraphs.append(teletype.extractText(elem))
        else:
            paragraphs.append(_extract_text_without_notes(elem))
    return "\n".join(paragraphs)


## --------- READ IN NEW BC DOCUMENTS
bctext = {}
for x, y in enumerate(bc['link']):
    try:
        bctext[x] = readtext(y)
    except Exception:
        bctext[x] = 'link_broken'
bc['TEXT'] = list(bctext.values())

## --------- READ IN NEW ADDENDUM DOCUMENTS
addtext = {}
for x, y in enumerate(add['link']):
    try:
        addtext[x] = readtext(y)
    except Exception:
        addtext[x] = 'link_broken'
add['TEXT'] = list(addtext.values())

with open(os.path.join(SCRIPT_DIR, 'doc_texts.pkl'), 'wb') as f:
    pickle.dump({'bc': bc, 'add': add}, f)
print(f"Saved doc texts to {os.path.join(SCRIPT_DIR, 'doc_texts.pkl')}")
