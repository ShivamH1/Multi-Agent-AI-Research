from langchain.tools import tool
import requests
from bs4 import BeautifulSoup


@tool
def scraper(url: str) -> str:
    """
    Scrape and return clean text content from the a given URL for deeper reading or research
    """
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()

        return soup.get_text(separator=" ", strip=True)[:3000]

    except Exception as e:
        return f"Error scraping URL: {str(e)}"
