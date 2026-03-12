import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import pickle
from lxml import etree

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

url = "https://dashboard.iatistandard.org/publishers/fcdo/"
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')
datatable = soup.find_all('table', class_="exploring-data")
fcdolinks = datatable[0].find_all("a", string="Source Url")
fcdolinks = [x.get("href") for x in fcdolinks]
fcdolinks = [link for link in fcdolinks if 'xml' in link]
fcdolinks = [link for link in fcdolinks if 'organisation' not in link]

##-----------------------------------------------------------------------
## GET LINKS TO PROJECT DOCUMENTS

def read_xml(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return etree.fromstring(response.content)
    except requests.exceptions.RequestException:
        return "fail"

collectdocs = {}

for lnk in fcdolinks:
    proj = re.sub(r".*/", "", lnk)
    proj = re.sub(r"\.xml$", "", proj)
    link = read_xml(lnk)
    if link == "fail":
        continue
    docnodes = link.xpath("//document-link/title/narrative")
    if len(docnodes) == 0:
        continue
    docnarr = [node.text for node in docnodes]
    doclink = [node.xpath('../..')[0].attrib.get('url') for node in docnodes]
    docid   = [node.xpath('../../../*')[0].text for node in docnodes]
    docttl  = [node.xpath('../../../title/narrative')[0].text for node in docnodes]
    docs = pd.DataFrame({
        "narrative": docnarr,
        "link":      doclink,
        "parent":    docid,
        "proj":      proj,
        "title":     docttl,
    })
    collectdocs[proj] = docs

collectdocs = pd.concat(collectdocs, ignore_index=True)
collectdocs = collectdocs.drop_duplicates()
collectdocs.loc[:, 'narrative'] = collectdocs['narrative'].str.lower()

collectdocs.loc[:, 'LF']  = collectdocs['narrative'].str.contains(r"logical ?framework").astype(int)
collectdocs.loc[:, 'PCR'] = collectdocs['narrative'].str.contains(r"project ?completion ?review").astype(int)
collectdocs.loc[:, 'AR']  = collectdocs['narrative'].str.contains(r"annual ?review").astype(int)
collectdocs.loc[:, 'BC']  = collectdocs['narrative'].str.contains(r"business ?case").astype(int)
collectdocs.loc[:, 'IS']  = collectdocs['narrative'].str.contains(r"intervention ?summary").astype(int)

# Just ex-DFID bits
dfid = collectdocs[
    (~collectdocs["parent"].str.contains('GOV-3')) &
    ((collectdocs.AR == 1) | (collectdocs.BC == 1) | (collectdocs.PCR == 1))
].copy()
dfid.loc[:, 'ADD'] = dfid['narrative'].str.contains(r'addendum', case=False).astype(int)

bc  = dfid[(dfid.ADD == 0) & (dfid.BC == 1)].copy()
add = dfid[(dfid.ADD == 1) & (dfid.BC == 1)].copy()

with open(os.path.join(SCRIPT_DIR, 'doc_links.pkl'), 'wb') as f:
    pickle.dump({'bc': bc, 'add': add}, f)
print(f"Saved doc links to {os.path.join(SCRIPT_DIR, 'doc_links.pkl')}")
