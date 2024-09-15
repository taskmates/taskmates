import os
from googleapiclient.discovery import build


def advanced_google_search(
        q, **kwargs
        # c2coff: str = "0",
        # cr: str = "countryBR",
        # dateRestrict: str = None,
        # exactTerms: str = None, excludeTerms: str = None, fileType: str = None,
        # filter: str = "1", gl: str = None, highRange: str = None,
        # hl: str = None, hq: str = None, imgColorType: str = None, imgDominantColor: str = None,
        # imgSize: str = None, imgType: str = None, linkSite: str = None,
        # lowRange: str = None, lr: str = None, num: int = 10, orTerms: str = None,
        # q: str = None,
        # relatedSite: str = None, rights: str = None, safe: str = "off",
        # searchType: str = None, siteSearch: str = None, siteSearchFilter: str = None,
        # sort: str = None, start: int = 0
):
    """
    Conducts a Google search with various parameters.

    Parameters:
    c2coff (str): Enables/disables Simplified and Traditional Chinese Search. Default is "0" (enabled).
    cr (str, optional): Restricts search results to documents originating in a particular country.
    cx (str, optional): The Programmable Search Engine ID for the request.
    dateRestrict (str, optional): Restricts results based on date (e.g., 'd7' for past 7 days).
    exactTerms (str, optional): Phrase that must be in all documents in the search results.
    excludeTerms (str, optional): Word or phrase that should not appear in any search results.
    fileType (str, optional): Restricts results to files of a specified extension.
    filter (str): Controls duplicate content filter ("0" for off, "1" for on).
    gl (str, optional): Geolocation of end user (two-letter country code).
    highRange (str, optional): Ending value for a search range.
    hl (str, optional): Sets the user interface language.
    hq (str, optional): Appends additional query terms to the search query.
    imgColorType (str, optional): Returns specific image color types (e.g., "color", "gray").
    imgDominantColor (str, optional): Returns images of a specific dominant color.
    imgSize (str, optional): Returns images of a specified size (e.g., "large", "medium").
    imgType (str, optional): Returns images of a specific type (e.g., "photo", "clipart").
    linkSite (str, optional): Specifies all search results should contain a link to a particular URL.
    lowRange (str, optional): Starting value for a search range.
    lr (str, optional): Restricts search to documents in a particular language.
    num (int): Number of search results to return (between 1 and 10).
    orTerms (str, optional): Additional search terms where results must contain at least one.
    q (str, optional): The search query.
    relatedSite (str, optional): Specifies all results should be pages related to a specified URL.
    rights (str, optional): Filters based on licensing (e.g., "cc_publicdomain").
    safe (str): Search safety level ("active" for SafeSearch, "off" for no filtering).
    searchType (str, optional): Specifies the search type ("image" for image search).
    siteSearch (str, optional): Specifies a particular site to always include or exclude from results.
    siteSearchFilter (str, optional): Controls whether to include or exclude siteSearch results.
    sort (str, optional): Sort expression to apply to the results (e.g., "date").
    start (int): The index of the first result to return (for pagination).

    Returns:
    list[dict]: A list of dictionaries containing search results.
    """

    api_key = os.environ["GOOGLE_API_KEY"]
    cse_id = os.environ["GOOGLE_CSE_ID"]
    service = build("customsearch", "v1", developerKey=api_key)
    response = service.cse().list(q=q, cx=cse_id, **kwargs).execute()
    return response


if __name__ == '__main__':
    results = advanced_google_search(q='Python', cr='countryBR', lr='lang_pt')
    for result in results.get('items', []):
        print(result.get('htmlTitle'))
        print(result.get('link'))
        print(result.get('htmlSnippet'))
        print()
