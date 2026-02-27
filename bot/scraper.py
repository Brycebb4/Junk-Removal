import requests
from bs4 import BeautifulSoup

class CincinnatiCraigslistScraper:
    def __init__(self):
        self.base_url = 'https://cincinnati.craigslist.org'
        self.listing_url = f'{self.base_url}/search/jJJ'

    def get_listings(self):
        response = requests.get(self.listing_url)
        if response.status_code == 200:
            return self.parse_listings(response.text)
        else:
            print('Failed to retrieve listings')
            return []

    def parse_listings(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        listings = []
        for item in soup.find_all('li', class_='result-row'):
            title = item.find('a', class_='result-title').text
            link = item.find('a', class_='result-title')['href']
            listings.append({'title': title, 'link': link})
        return listings

    def scrape(self):
        leads = self.get_listings()
        for lead in leads:
            print(f"Title: {lead['title']}, Link: {lead['link']}")