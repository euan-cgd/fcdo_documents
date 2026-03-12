import os
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import re
import pickle
from lxml import etree
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    parser = argparse.ArgumentParser(description="Create basic FCDO project data.")
    parser.add_argument("filepath", help="Path to save the output CSV")
    args = parser.parse_args()
    filepath = args.filepath

    url = "https://dashboard.iatistandard.org/publishers/fcdo/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    datatable = soup.find_all('table', class_="exploring-data")
    fcdolinks = datatable[0].find_all("a", string="Source Url")
    fcdolinks = [x.get("href") for x in fcdolinks]
    fcdolinks = [link for link in fcdolinks if 'xml' in link]
    fcdolinks = [link for link in fcdolinks if 'organisation' not in link]

    def read_xml(url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return etree.fromstring(response.content)
        except requests.exceptions.RequestException:
            return "fail"

    # GET WHETHER PROJECT HAS CLIMATE FINANCE (ICF) TAG
    def getICF(Node):
        codes = [node.attrib.get("code") for node in Node.xpath("tag")]
        return "ICF" in codes if codes else False

    def types(cat):
        return [i.xpath(cat)[0].attrib.get("code") if len(i.xpath(cat)) > 0 else "" for i in activities]

    # GET OECD GENDER POLICY MARKER
    def getgender(Node):
        codes = [node.attrib.get("code") for node in Node.xpath("policy-marker")]
        focus = [node.attrib.get("significance") for node in Node.xpath("policy-marker")]
        return focus[codes == 1] if len(codes) > 0 and '1' in codes else "NA"

    # GET PROJECT DATES
    def getdates(Node, num):
        dates = [node.attrib.get("iso-date") for node in Node.xpath("activity-date")]
        types_arr = np.array([node.attrib.get("type") for node in Node.xpath("activity-date")])
        return dates[np.where(types_arr == num)[0][0]] if len(dates) > 0 and num in types_arr else "NA"

    # GET SUM OF BUDGETS
    def budgetSum(Node):
        test1 = [node.text for node in Node.xpath("budget/value")]
        return sum(map(float, test1))

    # GET SECTOR CODES
    def getsectors(Node, var):
        secs = [node.attrib.get("code") for node in Node.xpath(var)]
        return ";".join(secs)

    # GET SECTOR PERCENTAGES
    def getsector_pct(Node, var):
        secs = [node.attrib.get("percentage") for node in Node.xpath(var)]
        try:
            return ";".join(secs)
        except Exception:
            return "1"

    collect = {}

    for lnk in fcdolinks:
        proj = re.sub(r".*/", "", lnk)
        proj = re.sub(r"\.xml$", "", proj)
        link = read_xml(lnk)
        if link == "fail":
            continue
        activities = link.xpath("//iati-activity")

        ids      = [node.xpath("iati-identifier")[0].text for node in activities]
        ttl      = [node.xpath("title/narrative")[0].text for node in activities]
        dsc      = [node.xpath("description/narrative")[0].text for node in activities]
        icf      = [getICF(node) for node in activities]
        gen      = [getgender(node) for node in activities]
        bud      = [budgetSum(node) for node in activities]
        st1      = [getdates(node, '1') for node in activities]
        st2      = [getdates(node, '2') for node in activities]
        st3      = [getdates(node, '3') for node in activities]
        st4      = [getdates(node, '4') for node in activities]
        sec      = [getsectors(node, "sector") for node in activities]
        sec_pct  = [getsector_pct(node, "sector") for node in activities]
        iso      = [getsectors(node, "recipient-country") for node in activities]
        iso_pct  = [getsector_pct(node, "recipient-country") for node in activities]

        collect[proj] = pd.DataFrame({
            'id':          ids,
            'iatipage':    proj,
            'title':       ttl,
            'description': dsc,
            'icf':         icf,
            'gender':      gen,
            'budget':      bud,
            'planstart':   st1,
            'actualstart': st2,
            'planend':     st3,
            'actualend':   st4,
            'sectors':     sec,
            'sector_pct':  sec_pct,
            'countries':   iso,
            'country_pct': iso_pct,
            'aid_t':       types("default-aid-type"),
            'finance_t':   types("default-finance-type"),
            'colab':       types("collaboration-type"),
        })

    result = pd.concat(collect.values(), axis=0)
    result['parent'] = result['id'].str.replace(r"-\d{3}$", "", regex=True)

    result_grouped = result.groupby('parent').agg({'budget': 'sum'}).reset_index()
    result_grouped = result_grouped.rename(columns={'budget': 'budget_sum'})

    result = result[result['id'].str.contains(r'\d{6}$')]
    result = pd.merge(result, result_grouped, on="parent", how="left")
    result = result.drop(columns=["budget"])

    result.to_csv(filepath, index=False)
    print(f"Saved full result to {filepath}")

    with open(os.path.join(SCRIPT_DIR, 'basic_data.pkl'), 'wb') as f:
        pickle.dump(result_grouped, f)
    print(f"Saved budget lookup to {os.path.join(SCRIPT_DIR, 'basic_data.pkl')}")

if __name__ == "__main__":
    main()
