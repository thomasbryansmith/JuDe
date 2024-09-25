from bs4 import BeautifulSoup
import requests
import os
from tqdm import tqdm
import re
import pandas as pd
import shutil
from datetime import datetime

url = "https://law.justia.com/cases/federal"

req = requests.get(url, headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
soup = BeautifulSoup(req.text, "html.parser")


# Federal Court of Appeals

fed_coas = soup.find_all("ul", {"class": "indented"})
fed_coas = [fed_coa.find_all("a", href=True) for fed_coa in fed_coas]
fed_coas = [fed_coa.get('href') for fed_coa in fed_coas[1]]


# Federal District Courts

fed_dcs = soup.find_all("ul", {"class": "list-columns list-columns-three list-no-styles"})
fed_dcs = [fed_dc.find_all("a", href=True) for fed_dc in fed_dcs]
fed_dcs = [fed_dc.get('href') for fed_dc in fed_dcs[0]]

for i in range(0,len(fed_dcs)):
    url = "https://law.justia.com" + fed_dcs[i]

    req = requests.get(url, headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    soup = BeautifulSoup(req.text, "html.parser")

    dcs = soup.find_all("div", {"class": "indented"})
    dcs = [dc.find_all("a", href=True) for dc in dcs]
    fed_dcs[i] = [dc.get('href') for dc in dcs[0]]

fed_dcs = sum([v if isinstance(v, list) else [v] for v in fed_dcs],[])


# State Courts

url = "https://law.justia.com/cases"

req = requests.get(url, headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
soup = BeautifulSoup(req.text, "html.parser")

scas = soup.find_all("ul", {"class": "list-columns list-columns-three list-no-styles"})
scas = [sca.find_all("a", href=True) for sca in scas]
scas = [sca.get('href') for sca in scas[1]]

for i in range(0,len(scas)):
    url = "https://law.justia.com" + scas[i]

    req = requests.get(url, headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    soup = BeautifulSoup(req.text, "html.parser")

    sc = soup.find_all("div", {"class": "indented"})
    sc = [c.find_all("a", href=True) for c in sc]
    scas[i] = [c.get('href') for c in sc[0]]

scas = sum([v if isinstance(v, list) else [v] for v in scas],[])


# Combined urls
courts = fed_coas + fed_dcs + scas

def slugify(value):
    """Converts text into a directory-friendly format. 

    Args:
        value (string): input text for conversion

    Returns:
        string: converted text
    """
    import re
    
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    value = re.sub('[-\s]+', '-', value)
    value = re.sub('^_|_$','', value)

    return value



def justia_scrape(years, court):
    """Scrapes portable document format (PDF) legal opinion documents from law.justia.com.
    The script or Jupyter JSON file that executes this function must be located in the root
    alongside a subdirectory named "data", within which there must be a "court_opinions" 
    subdirectory. This function will create a directory structure within the "court_opinions" 
    subdirectory, arranging downloaded PDFs by year and court. 

    Args:
        years (list): list of years for which you wish to download data.
        court (string): target court, must match law.justia.com URL format. See the 'courts' object.
    """
    print("+++ " + str(datetime.now()) + " +++\n")
    print("//LAWJUSTIASCRAPER")
    print("//"+court.upper()+"\n")
    
    os.mkdir(".\\data\\court_opinions\\" +
             re.sub("^_|_$","",re.sub("/","_",str(court))))
    
    for year in years:
        print("+++ " + str(year))
        
        url = "https://law.justia.com" + court + str(year) + "/"
        req = requests.get(url, headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        soup = BeautifulSoup(req.text, "html.parser")
        
        pages = soup.find_all("span", {"class": "pagination page"})
        pages = [page.find_all("a", href=True) for page in pages]
        pages = [page[0].get('href') if len(page) > 0 else '' for page in pages]
        pages = [page for page in pages if page]
        pages = [i for n, i in enumerate(pages) if i not in pages[:n]]
        
        urls = [url] + ["https://law.justia.com" + page for page in pages]
        reqs = [requests.get(url, headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}) for url in urls]
        
        print("Parsing: " + str(len(reqs)) + " page(s)")

        citations = []
        links = []
        for req in reqs:
            soup = BeautifulSoup(req.text, "html.parser")
            opinions = soup.find_all("div", {"class": "has-padding-content-block-30 -zb"})
            
            temp = [opinion.find_all("a", {"class": "case-name"}, href=True) for opinion in opinions]
            temp = [link[0].get('href') if len(link) > 0 else 'No Link' for link in temp]
            temp = [re.sub("/","_",re.sub("^/cases/|.html$","",citation)) for citation in temp]
            citations = citations + temp

            temp = [opinion.find_all("a", {"class": "case-name"}, href=True) for opinion in opinions]
            temp = ['https://law.justia.com' + link[0].get('href') if len(link) > 0 else 'No Link' for link in temp]
            links = links + temp
            

        df = pd.DataFrame([{'citation': citation, 'url': link} for citation, link in zip(citations, links)])
        r2 = 'Dropping: ' + str(len(df[df['url'] == 'No Link']))
        df = df.drop(df[df['url'] == 'No Link'].index)
        r1 = 'Collecting: ' + str(len(df))

        print(r1)
        print(r2)

        os.mkdir(".\\data\\court_opinions\\" + 
                 re.sub("^_|_$","",re.sub("/","_",str(court))) + "\\" + 
                 str(year))

        for url, citation in tqdm(zip(df.url, df.citation)):
            req = requests.get(url, headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            soup = BeautifulSoup(req.text, "html.parser")
            link = soup.find_all("a", {"class": "pdf-icon pull-right has-margin-bottom-20"}, href=True)
            if len(link)!=0:
                link = "https:" + link[0].get('href')
                response = requests.get(link, 'wb') 
                if response.status_code==200:
                    pdf = open(".\\data\\court_opinions\\" + 
                            re.sub("^_|_$","",re.sub("/","_",str(court))) + "\\" + 
                            str(year) + "\\" + 
                            slugify(str(citation)) + ".pdf", "wb")
                    pdf.write(response.content)
                    pdf.close()
                else: 
                    print('Error: ' + 
                        re.sub(".pdf$", "", str(citation)).upper() + 
                        ' aborted with ' + 
                        str(response.status_code) + 
                        ' status')
        print(" ")
        
        
        
def court_search(text):
    """searches the courts object, a list of valid input strings for the justia_scrape function.

    Args:
        text (string): input search string

    Returns:
        list: all strings containing the search term
    """
    output = []
    
    for court in courts:
        if text.lower() in court:
            output.append(court)
            
    return output