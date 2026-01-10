from ddgs import DDGS

def get_search(query: str) -> str:
    """
    Search DuckDuckGo for a given query and return recent results (past week).
    
    Args:
        query (str): The search query.
    
    Returns:
        str: A formatted string of the top search results.
    """
    try:
        results = DDGS().text(query=query, region="wt-wt", safesearch="off", timelimit="w", max_results=20)
        # print(results)
        if not results:
            return f"No recent results found for '{query}'."
            
        formatted_results = []
        for r in results:
            title = r.get('title', 'No Title')
            link = r.get('url', r.get('href', 'No Link'))
            date = r.get('date', 'No Date')
            snippet = r.get('body', r.get('snippet', 'No Snippet'))
            source = r.get('source', 'Unknown Source')
            formatted_results.append(f"Title: {title}\nSource: {source}\nDate: {date}\nLink: {link}\nSnippet: {snippet}")
            
        return "\n\n".join(formatted_results)
        
    except Exception as e:
        return f"Error performing DuckDuckGo search: {str(e)}"

def get_news_search(query: str) -> str:
    """
    Search DuckDuckGo News for a given query and return recent results (past week).
    
    Args:
        query (str): The search query.
    
    Returns:
        str: A formatted string of the top search results.
    """
    try:
        results = DDGS().news(query=query, region="wt-wt", safesearch="off", timelimit="w", max_results=20)
        # print(results)
        if not results:
            return f"No recent results found for '{query}'."
            
        formatted_results = []
        for r in results:
            title = r.get('title', 'No Title')
            link = r.get('url', r.get('href', 'No Link'))
            date = r.get('date', 'No Date')
            snippet = r.get('body', r.get('snippet', 'No Snippet'))
            source = r.get('source', 'Unknown Source')
            formatted_results.append(f"Title: {title}\nSource: {source}\nDate: {date}\nLink: {link}\nSnippet: {snippet}")
            
        return "\n\n".join(formatted_results)
        
    except Exception as e:
        return f"Error performing DuckDuckGo search: {str(e)}"

if __name__ == "__main__":
    print(searc("Tennessee"))
