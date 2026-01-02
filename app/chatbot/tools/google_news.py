import requests
from bs4 import BeautifulSoup
import urllib.parse

def get_google_news(query):
    """
    Fetch recent news from Google News RSS for a given query.
    
    Args:
        query (str): The search query.
        
    Returns:
        str: A formatted string of the top news items.
    """
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')[:5]  # Get top 5 items
        
        if not items:
            return f"No news found for '{query}'."
            
        news_results = []
        for item in items:
            title = item.title.text if item.title else "No Title"
            link = item.link.text if item.link else "No Link"
            pub_date = item.pubDate.text if item.pubDate else "No Date"
            source = item.source.text if item.source else "Unknown Source"
            
            news_results.append(f"Title: {title}\nSource: {source}\nDate: {pub_date}\nLink: {link}")
            
        return "\n\n".join(news_results)
        
    except Exception as e:
        return f"Error fetching Google News: {str(e)}"

if __name__ == "__main__":
    # Test the function
    print(get_google_news("Nashville flash flood"))
