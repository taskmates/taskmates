"""Test different methods of passing stop parameter to LangChain LLM clients."""
import pytest
from langchain_core.messages import HumanMessage


@pytest.mark.integration
async def test_langchain_openai_stop_methods():
    """Test all methods of passing stop parameter to ChatOpenAI."""
    from langchain_openai import ChatOpenAI
    
    messages = [HumanMessage(content="Count from 1 to 10")]
    
    # Test constructor with invoke
    model = ChatOpenAI(model="gpt-4o-mini", stop=["5"])
    response = await model.ainvoke(messages)
    assert "5" not in response.content
    assert "6" not in response.content
    
    # Test model_kwargs with invoke
    model = ChatOpenAI(model="gpt-4o-mini", model_kwargs={"stop": ["5"]})
    response = await model.ainvoke(messages)
    assert "5" not in response.content
    assert "6" not in response.content
    
    # Test invoke parameter
    model = ChatOpenAI(model="gpt-4o-mini")
    response = await model.ainvoke(messages, stop=["5"])
    assert "5" not in response.content
    assert "6" not in response.content
    
    # Test astream parameter - works
    model = ChatOpenAI(model="gpt-4o-mini")
    chunks = []
    async for chunk in model.astream(messages, stop=["5"]):
        chunks.append(chunk)
    content = ''.join(c.content for c in chunks if c.content)
    assert "5" not in content
    assert "6" not in content


@pytest.mark.integration
async def test_langchain_anthropic_stop_methods():
    """Test all methods of passing stop parameter to ChatAnthropic."""
    from langchain_anthropic import ChatAnthropic
    
    messages = [HumanMessage(content="Count from 1 to 10")]
    
    # Test constructor with invoke
    model = ChatAnthropic(model="claude-haiku-4-5", stop=["5"])
    response = await model.ainvoke(messages)
    assert "5" not in response.content
    assert "6" not in response.content
    
    # Test model_kwargs with invoke
    model = ChatAnthropic(model="claude-haiku-4-5", model_kwargs={"stop": ["5"]})
    response = await model.ainvoke(messages)
    assert "5" not in response.content
    assert "6" not in response.content
    
    # Test invoke parameter
    model = ChatAnthropic(model="claude-haiku-4-5")
    response = await model.ainvoke(messages, stop=["5"])
    assert "5" not in response.content
    assert "6" not in response.content
    
    # Test astream parameter - works
    model = ChatAnthropic(model="claude-haiku-4-5")
    chunks = []
    async for chunk in model.astream(messages, stop=["5"]):
        chunks.append(chunk)
    content = ''.join(c.content for c in chunks if c.content)
    assert "5" not in content
    assert "6" not in content


@pytest.mark.integration
async def test_langchain_xai_stop_methods():
    """Test all methods of passing stop parameter to ChatXAI."""
    from langchain_xai import ChatXAI
    import os
    
    messages = [HumanMessage(content="Count from 1 to 10")]
    api_key = os.getenv("XAI_API_KEY")
    
    # Test constructor
    with pytest.raises(Exception):
        model = ChatXAI(model="grok-4-latest", api_key=api_key, stop=["5"])
        await model.ainvoke(messages)
    
    # Test model_kwargs
    with pytest.raises(Exception):
        model = ChatXAI(model="grok-4-latest", api_key=api_key, model_kwargs={"stop": ["5"]})
        await model.ainvoke(messages)
    
    # Test invoke
    with pytest.raises(Exception):
        model = ChatXAI(model="grok-4-latest", api_key=api_key)
        await model.ainvoke(messages, stop=["5"])
    
    # Test astream
    with pytest.raises(Exception):
        model = ChatXAI(model="grok-4-latest", api_key=api_key)
        chunks = []
        async for chunk in model.astream(messages, stop=["5"]):
            chunks.append(chunk)


@pytest.mark.integration
async def test_langchain_google_genai_stop_methods():
    """Test all methods of passing stop parameter to ChatGoogleGenerativeAI."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    messages = [HumanMessage(content="Count from 1 to 10")]
    
    # Test constructor - accepts parameter (with warning) but behavior is inconsistent
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", stop=["5"])
    response = await model.ainvoke(messages)
    assert response.content is not None
    
    # Test model_kwargs - accepts parameter (with warning) but behavior is inconsistent
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", model_kwargs={"stop": ["5"]})
    response = await model.ainvoke(messages)
    assert response.content is not None
    
    # Test invoke - accepts parameter but behavior is inconsistent
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    response = await model.ainvoke(messages, stop=["5"])
    assert response.content is not None
    
    # Test astream - raises ValueError
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    with pytest.raises(ValueError, match="No generation chunks were returned"):
        chunks = []
        async for chunk in model.astream(messages, stop=["5"]):
            chunks.append(chunk)


@pytest.mark.integration
async def test_langchain_ollama_stop_methods():
    """Test all methods of passing stop parameter to ChatOllama."""
    from langchain_ollama import ChatOllama
    
    messages = [HumanMessage(content="Count from 1 to 10")]
    
    # Test constructor - accepts parameter but behavior is inconsistent
    model = ChatOllama(model="gpt-oss:20b", base_url="http://localhost:11434", stop=["5"])
    response = await model.ainvoke(messages)
    assert response.content is not None
    
    # Test model_kwargs - accepts parameter but behavior is inconsistent
    model = ChatOllama(model="gpt-oss:20b", base_url="http://localhost:11434", model_kwargs={"stop": ["5"]})
    response = await model.ainvoke(messages)
    assert response.content is not None
    
    # Test invoke - accepts parameter but behavior is inconsistent
    model = ChatOllama(model="gpt-oss:20b", base_url="http://localhost:11434")
    response = await model.ainvoke(messages, stop=["5"])
    assert response.content is not None
    
    # Test astream - accepts parameter but behavior is inconsistent
    model = ChatOllama(model="gpt-oss:20b", base_url="http://localhost:11434")
    chunks = []
    async for chunk in model.astream(messages, stop=["5"]):
        chunks.append(chunk)
    assert len(chunks) > 0


@pytest.mark.integration
@pytest.mark.integration
async def test_langchain_openai_stop_with_web_search_tool():
    """Test that stop parameter fails with web_search_tool in astream()."""
    from langchain_openai import ChatOpenAI
    
    messages = [HumanMessage(content="What's the weather in San Francisco?")]
    
    # Web search tool uses responses API which doesn't accept stop in astream
    web_search_tool = {"type": "web_search_preview"}
    model = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools([web_search_tool])
    
    # This should fail because responses API doesn't accept stop parameter
    with pytest.raises(TypeError, match="got an unexpected keyword argument 'stop'"):
        chunks = []
        async for chunk in model.astream(messages, stop=["5"]):
            chunks.append(chunk)

async def test_fixture_chat_model_stop_methods():
    """Test all methods of passing stop parameter to FixtureChatModel."""
    from taskmates.core.workflows.markdown_completion.completions.llm_completion.testing.fixture_chat_model import FixtureChatModel
    
    messages = [HumanMessage(content="Count from 1 to 10")]
    
    # Test constructor
    with pytest.raises(Exception):
        model = FixtureChatModel(model="fixture", stop=["5"])
        await model.ainvoke(messages)
    
    # Test model_kwargs
    with pytest.raises(Exception):
        model = FixtureChatModel(model="fixture", model_kwargs={"stop": ["5"]})
        await model.ainvoke(messages)
    
    # Test invoke
    with pytest.raises(Exception):
        model = FixtureChatModel(model="fixture")
        await model.ainvoke(messages, stop=["5"])
    
    # Test astream
    with pytest.raises(Exception):
        model = FixtureChatModel(model="fixture")
        chunks = []
        async for chunk in model.astream(messages, stop=["5"]):
            chunks.append(chunk)
