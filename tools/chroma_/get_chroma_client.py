import os



# Define an async version of get_chroma_client
def get_chroma_client(path=".chromadb"):
    import chromadb
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    chroma_client = chromadb.PersistentClient(path=path)
    return chroma_client
