from langchain.tools import tool
from tavily import TavilyClient
import os
from dotenv import load_dotenv

load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


@tool
def web_search(query: str) -> str:
    """
    Search the web for recent and reliable information on a topic. Returns Title, URLs and a short snippet on the topic.
    """
    results = tavily.search(query=query, max_results=5)

    results_to_return = []

    for r in results["results"]:
        results_to_return.append(
            f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['content'][:300]}\n"
        )

    return "\n------------------------------------------------------------------------------\n".join(
        results_to_return
    )
