import argparse
import asyncio
import os

import yaml
from googleapiclient.discovery import build


async def google_search(
        q,
        cr=None,
        gl=None,
        lr=None,
        num=5,
        format="simplified_yaml"):
    """
    Conducts a Google search. When using the `google_search` tool, it is important to match the language of your search query (`q`) with
    the country (`gl`) and language (`lr`) parameters you specify. This ensures that the search results are relevant to
     the desired region and language audience. Example: If you are searching for content in Germany and in German,
     your query `q` should be in German regardless of whether the user asked you in English, and you should set `gl` to 'DE' and
      `lr` to 'lang_de'.

    Parameters:
    cr (str, optional): Restricts search results to documents originating in a particular country. Ex: countryUS
    gl (str, optional): Geolocation of end user (two-letter country code).
    lr (str, optional): Restricts search to documents in a particular language.
    q (str, optional): The search query. MUST BE written in the same language of `lr`
    num (int, optional): Number of search results to return. Default is 5.

    Returns:
    list[dict]: Search Results
    """

    api_key = os.environ["GOOGLE_API_KEY"]
    cse_id = os.environ["GOOGLE_CSE_ID"]
    service = build("customsearch", "v1", developerKey=api_key)
    response = service.cse().list(cr=cr, gl=gl, lr=lr, q=q, cx=cse_id, num=num).execute()

    items = response.get('items', [])

    if format == "simplified_yaml":
        # Extract only the title, link, and snippet from each item
        simplified_items = [
            {'title': item['title'], 'link': item['link'], 'snippet': item['snippet']}
            for item in items
        ]

        # Convert the simplified search results to a YAML formatted string
        yaml_results = yaml.dump(simplified_items, sort_keys=False, default_flow_style=False, allow_unicode=True)

        return yaml_results

    else:
        return items


def main():
    # Set up the argument parser
    parser = argparse.ArgumentParser(description='Google Search Command Line Tool')
    parser.add_argument('--q', type=str, required=True, help='Search query')
    parser.add_argument('--cr', type=str, help='Country restriction (e.g., countryUS)')
    parser.add_argument('--gl', type=str, help='Geolocation of end user (e.g., US)')
    parser.add_argument('--lr', type=str, help='Language restriction (e.g., lang_en)')
    parser.add_argument('--num', type=int, default=5,
                        help='Number of search results to return (default: 5)')  # Add the num argument

    # Parse the arguments
    args = parser.parse_args()

    # Run the main function with the parsed arguments using asyncio.run()
    results = asyncio.run(google_search(q=args.q, cr=args.cr, gl=args.gl, lr=args.lr, num=args.num))
    print(results)


if __name__ == '__main__':
    main()
