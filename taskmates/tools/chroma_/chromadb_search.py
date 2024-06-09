import asyncio
import os

from taskmates.tools.chroma_.get_chroma_client import get_chroma_client


async def chromadb_search(query: str, n_results: int = 5):
    """
    Searches the chromadb for the given query and returns the top n results.

    :param query: The query to search for.
    :param n_results: The number of results to return.
    :return: A list of the top n results.
    """

    path: str = os.getenv("CHROMADB_PATH", "/Users/ralphus/Development/ai/chat-intellij-sdk/data/.chromadb")
    collection: str = os.getenv("CHROMADB_COLLECTION", "docs")
    topic: str = os.getenv("CHROMADB_TOPIC")

    chroma_client = get_chroma_client(path)
    chroma_collection = chroma_client.get_or_create_collection(name=collection)
    results = chroma_collection.query(query_texts=[query],
                                      include=["metadatas", "documents"],
                                      n_results=n_results)

    documents = results['documents']
    metadatas = results['metadatas']

    transformed_results = []
    for document, metadata in list(zip(documents, metadatas)):
        for doc_entry, metadata_entry in list(zip(document, metadata)):
            transformed_results.append({"document": doc_entry, "metadata": {"source": metadata_entry["source"]}})

    return transformed_results


# Convert main to an async function
async def main():
    path = "/Users/ralphus/Development/ai/chat-intellij-sdk/data/.chromadb"
    collection = "docs"
    query = "what are the base classes for tests and what are the differences between them?"

    os.environ["CHROMADB_PATH"] = path
    os.environ["CHROMADB_COLLECTION"] = collection
    response = await chromadb_search(query)
    print(response)


# Run the async main using asyncio
if __name__ == '__main__':
    asyncio.run(main())
