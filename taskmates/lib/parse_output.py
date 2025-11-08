from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field, ValidationError
from typeguard import typechecked
from typing import TypeVar, Optional

from taskmates.workflows.codebase_rag.constants import DEFAULT_MODEL_NAME

TModel = TypeVar('TModel', bound=BaseModel)


@typechecked
def parse_output(
    content: str,
    schema: type[TModel],
    model_name: str = DEFAULT_MODEL_NAME,
    max_retries: int = 1
) -> TModel:
    """
    Parse LLM output into a structured Pydantic model with validation and retry.

    Args:
        content: The text content to parse
        schema: Pydantic model class to parse into
        model_name: LLM model to use for parsing/correction
        max_retries: Maximum number of retry attempts on validation errors

    Returns:
        Parsed and validated instance of the schema

    Raises:
        ValidationError: If validation fails after all retries
    """
    parser = PydanticOutputParser(pydantic_object=schema)

    prompt = PromptTemplate(
        template=(
            "Extract the details from the text below.\n"
            "{format_instructions}\n\n"
            "Text:\n{input_text}"
        ),
        input_variables=["input_text"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    llm = ChatOllama(
        model=model_name,
        temperature=0
    )

    chain = prompt | llm | parser

    last_error: Optional[Exception] = None
    current_content = content

    for attempt in range(max_retries + 1):
        try:
            return chain.invoke({"input_text": current_content})
        except ValidationError as e:
            last_error = e
            if attempt < max_retries:
                # Create error correction prompt
                error_message = f"""ERROR: The previous response had validation errors:

{str(e)}

Please provide a corrected response that follows the schema exactly.

Original text:
{content}

{parser.get_format_instructions()}"""

                current_content = error_message
            else:
                # Last attempt failed, raise the error
                raise

    # Should never reach here, but just in case
    if last_error:
        raise last_error
    raise RuntimeError("Unexpected error in parse_output")


if __name__ == "__main__":
    text = "Maria Santos is a 34-year-old architect living in Lisbon."


    class Person(BaseModel):
        name: str = Field(description="Full name of the person")
        age: int = Field(description="Age in years")
        occupation: str = Field(description="Job or profession")


    result = parse_output(content=text, schema=Person)

    print(result)
    print(result.model_dump())  # as JSON
