Requirements
python 3+
	requests
	beautifulsoup4
	pyYAML

There are no proper CLI's for anything, yay for code that was intended to be a one off!

company_urls.txt is a collection of ~500 company url: job urls. Last updated in 8/16, company urls were orginally sourced from gamedevmap.

scrape_job_pages.py attempts to find jobs on the pages listed in company_urls.txt, and compare the results to the previous run. A diff is saved as update.txt, full results are saved as joblistings_current.txt. This is probably what you want.

find_job_pages.py attemps to find job pages for each main company page. This is takes a long time to run. Unless you have a new source of gamedev websites, or improve the crawler to find more job pages, you will probably never want to run this.

/extras has a joblistings from 2014 for posterity, and ~900 additional company urls where a job page could not be found by the crawler.