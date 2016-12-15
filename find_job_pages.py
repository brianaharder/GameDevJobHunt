import requests
import yaml
from bs4 import BeautifulSoup

import os.path

#dumb crawler options
url_endings = ['/','.php','.html','.asp','.htm']
url_keywords = ['jobs', 'careers', 'career', 'Jobs', 'wp/jobs', 'company/jobs', 'company/careers', 'openings']
keywords = ['job', 'career', 'hiring']

def get_company_URLs(list_url):
    """
    Get company urls from gamedevmap
    """
    r = requests.get(list_url)
    soup = BeautifulSoup(r.text)
    urls = []
    for cell in soup.find_all('b'):
        url = cell.find('a')
        if url:
            urls.append(url.get('href'))
    return urls


def get_jobs_page(company_url):
    """
    Try to navigate to a jobs page from a homepage
    """
    try:
        mainr = requests.get(company_url, timeout=5)
        if company_url[-1] != r"/":
            company_url += r"/"

        # Attempt to find a link on the main page to the jobs page
        potential_pages = []
        for link in BeautifulSoup(mainr.text).find_all('a'):
            is_job = False
            if link.text is not None:
                is_job = any([keyword == link.text.lower() for keyword in keywords])
            if not is_job and link.find('img') is not None and link.find('img').get('alt') is not None:
                is_job = any([keyword == link.find('img').get('alt').lower() for keyword in keywords])
            if is_job:
                try:
                    if link.get('href') not in potential_pages and '@' not in link.get('href'):
                        potential_pages.append(link.get('href'))
                except TypeError as e:
                    print("error on", company_url, link.text)
                    pass
        if len(potential_pages) >= 1:
            print("Found link!")
            jobpage = potential_pages[0]
            if jobpage[0] == '.' or jobpage[0] == r'/':
                jobpage = jobpage.strip(r'./')
                return company_url + jobpage
            elif jobpage[0] == "#":
                return company_url
            return jobpage




        # Look for a real page in one of the common places jobs pages live
        for ending in url_endings:
            for keyword in url_keywords:
                newurl = ''.join([company_url,keyword,ending])
                r = requests.get(newurl, timeout=1)
                if r.status_code == 200:
                    if '404' in r.text or 'Page not found' in r.text or 'Fatal error' in r.text or '506' in r.text or "Not Found" in r.text:
                        #print('{url} has faulty error codes'.format(url=newurl))
                        continue
                    elif r.text == mainr.text:
                        #print('{url} redirects to main page on bad pages'.format(url=newurl))
                        continue
                    elif len(r.text) < 100 or 'temporarily unavailable' in r.text:
                        #print('{url} not really a page'.format(url=newurl))
                        continue
                    else:
                        return newurl
        else:
            return ""
    except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError, requests.exceptions.TooManyRedirects, requests.exceptions.ReadTimeout) as e:
        #print("Cannot Connect to: ", company_url, e)
        return "Dead?"



def update_site_listings(urls_file='company_urls.txt', list_url=False,force=False):
    """
    Updates url files from a list_url
    Optional force to force it to regenerate ALL job page urls
    """
    if not os.path.exists(urls_file):
        f = open(urls_file, 'w')
        yaml.dump({"test": "testing"}, f)
        f.close()
    with open(urls_file, 'r') as company_urls:
        data = yaml.load(company_urls)
        #remake company urls if a list url is provided
        if list_url:
            new_urls = get_company_URLs(list_url)
            for url in new_urls:
                if url not in data and url+r"/" not in data and url.replace('https','http') not in data:
                    data[url] = ""
                    print('adding url', url)
            dump_yaml(data, urls_file)
        for url,jobspage in data.items():
            if force or jobspage == "":
                old = jobspage
                new = get_jobs_page(url)
                if new == "":
                    new = old
                else:
                    data[url] = new
                    print(url, ': ', data[url])
            else:
                pass

    dump_yaml(data,urls_file)


def dump_yaml(db, filename):
    with open(filename, 'w+') as f:
        yaml.safe_dump(db, f, encoding='utf-8', allow_unicode=True, default_flow_style=False)


def clean_list():
    """
    Tidy company urls if anything strange has happened to it
    """
    with open('company_urls.txt', 'r') as company_urls:
        data = yaml.load(company_urls)
        for url, joburl in data.items():
            print(type(joburl))
            if joburl is None or "http" not in joburl:
                data[url] = ""
            if url[-1] == r'/':
                alturl = url + r"/"
            else:
                alturl = url[:-1]
            if alturl in data:
                if len(data[alturl]) > len(joburl):
                    data.remove(url)
                else:
                    data.remove(alturl)
    dump_yaml(data, 'clean.txt')


#clean_list()
#update_site_listings(r"http://www.gamedevmap.com/index.php?location=&country=United%20States&state=&city=&query=&type=&start=1&count=2000", force=False)
update_site_listings('extras/company_urls_fails.txt')

