import requests
from bs4 import BeautifulSoup
import yaml

import re, os
from collections import Counter

re.IGNORECASE

def add_job_to_db(job_url,job_title,job_details):
    if job_details is None or job_title is None:
        return False
    if job_url not in Jobs_Database:
        Jobs_Database[job_url] = {}
    job_title = job_title.strip().split('\n')[0]
    job_details = job_details.strip()
    Jobs_Database[job_url][job_title] = job_details
    return True


def find_jobs_on_page(company_url,job_url):
    jobsfound = 0
    try:
        r = requests.get(job_url, timeout=1)
    except(requests.ConnectionError, requests.exceptions.ChunkedEncodingError, requests.exceptions.ReadTimeout) as e:
        print('could not fetch pages at {url}'.format(url=company_url))
        return False

    soup = BeautifulSoup(r.text)
    style = find_job_style_2(soup)
    jobs = find_all_with_style(soup, style)

    for job in jobs:
        link = job.find('a')
        if link and link.get('href'):
            url = link.get('href').strip()
            job_title = link.string
        else:
            url = job_url.strip()
            job_title = job.string
        if add_job_to_db(job_url,job_title,url):
            jobsfound += 1
    if jobsfound == 0:
        pass
        # print('Nothing found at {url}'.format(url=job_url))


def find_job_style_2(soup):
    styles = find_potential_job_styles(soup)
    if not styles:
        return False
    passed_test = []
    for style in styles:
        matches = find_all_with_style(soup, style)
        if any(match.string and len(match.string) > 100 for match in matches):
            pass
        else:
            passed_test.append(style)
    #if len(passed_test) > 1:
    #    print("multiple passes", matches)
    if len(passed_test) == 0:
        return False
    return Counter(passed_test).most_common(1)[0][0]



def find_potential_job_styles(soup):
    def codify_style(tag):
        keys = []
        for key,value in tag.attrs.items():
            if type(key) == list:
                keys.extend(key)
            else:
                keys.append(key)
        return tag.name, tuple(keys)

    def getstyles(potentialmatches):
        if len(potentialmatches) == 0:
            return False
        styles = []
        for match in potentialmatches:
            disqualified_styles = []
            style = []
            for parent in match.parents:
                style.append(codify_style(parent))
            styles.append(tuple(style))
        return styles

    regex = '|'.join(job_words) + r'\b'
    disqualification_regex = '|'.join(job_exceptions) + r'\b'
    potentialmatches = [match for match in soup.find_all(text=re.compile(regex))
                        if len(match.string) < 100 and not re.match(disqualification_regex, match.string)]
    return getstyles(potentialmatches)


def find_all_with_style(soup, styles):
    def match_style(matches,style):
        working = []
        for original,match in matches:
            goodmatch = True
            if match.name == style[0]:
                for attr in style[1]:
                    if match.get(attr) == None:
                        goodmatch = False
                for attr in match.attrs:
                    if attr not in style[1]:
                        goodmatch = False
                if goodmatch:
                    working.append((original,match.parent))
        return working

    def matchattrs(matches, style):
        working = []
        for match in matches:
            for attr in style[1]:
                if match.get(attr) == None:
                    break
            else:
                working.append((match, match.parent))
        return working
    if styles:
        matches = soup.find_all(styles[0][0])  # MAGIC NUMBERS SORRY
        matches = matchattrs(matches, styles[0])

        for style in styles[1:-1]:  # ...why?
            matches = match_style(matches, style)
        return [match[0] for match in matches]
    else:
        return []


def compare_joblists(old_filename,new_filename):
    def safe_writelines(output, lines):
        try:
            output.writelines(lines)
        except UnicodeEncodeError:
            for line in lines:
                try:
                    output.write(line)
                except UnicodeEncodeError:
                    print('Could not write', line.strip())
    class DictDiffer(object):
        """
        Calculate the difference between two dictionaries as:
        (1) items added
        (2) items removed
        (3) keys same in both but changed values
        (4) keys same in both and unchanged values
        """
        def __init__(self, current_dict, past_dict):
            self.current_dict, self.past_dict = current_dict, past_dict
            self.set_current, self.set_past = set(current_dict.keys()), set(past_dict.keys())
            self.intersect = self.set_current.intersection(self.set_past)
        def added(self):
            return self.set_current - self.intersect
        def removed(self):
            return self.set_past - self.intersect
        def changed(self):
            return set(o for o in self.intersect if self.past_dict[o] != self.current_dict[o])
        def unchanged(self):
            return set(o for o in self.intersect if self.past_dict[o] == self.current_dict[o])

    with open('update.txt', 'w+') as output:
        old_data = yaml.load(open(old_filename, 'r+'))
        new_data = yaml.load(open(new_filename, 'r+'))
        diff = DictDiffer(new_data, old_data)
        for company in diff.changed():
            if not isinstance(new_data[company], dict) and not isinstance(old_data[company], dict):
                continue
            company_diff = DictDiffer(new_data[company],old_data[company])
            output.write(company + '\n')
            if company_diff.added():
                output.write('--added--\n')
                safe_writelines(output, [item + '\n' for item in company_diff.added()])
                output.write('\n')
            if company_diff.removed():
                output.write('--removed--\n')
                safe_writelines(output, [item + '\n' for item in company_diff.removed()])
                output.write('\n')


def dump_yaml(db, filename):
    with open(filename, 'w+') as f:
        yaml.safe_dump(db, f, encoding='utf-8', default_flow_style=False)


def record_all_joblistings():
    with open('company_urls.txt', 'r') as company_urls:
        data = yaml.load(company_urls)
        for company_url, job_url in data.items():
            if 'http' in job_url:
                find_jobs_on_page(company_url,job_url)
        Jobs_Database['No Jobs Found'] = []
        for company_url, job_url in data.items():
            if job_url not in Jobs_Database or Jobs_Database[job_url] == {}:
                Jobs_Database['No Jobs Found'].append(job_url)
    dump_yaml(Jobs_Database, 'joblistings_current.txt')


def find_new_jobs():
    os.rename('joblistings_current.txt', 'joblistings_old.txt')
    record_all_joblistings()
    compare_joblists('joblistings_old.txt', 'joblistings_current.txt')
    os.remove('joblistings_old.txt')


job_words = ['Designer', 'Artist', 'Programmer', 'Engineer', 'Director', 'Animator', 'Producer', 'Developer',
             'Assurance', 'Marketing', 'Intern', 'Administrator', 'Tester', 'Manager', 'QA', 'Development', 'Lead']
job_exceptions = ['skills', 'Qualifications', 'Requirements', 'Responsibilities', 'career', 'please', 'hiring', 'broad',
                  'Experience', 'motivate', 'Flexible', 'salary']


Jobs_Database = {}
find_new_jobs()

