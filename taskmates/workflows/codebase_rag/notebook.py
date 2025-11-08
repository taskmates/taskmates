import asyncio
from taskmates.core.workflow_engine.transaction_manager import TransactionManager, runtime
from taskmates.workflows.codebase_rag.sdk.answer_question import answer_question

"""
CRITICAL DESIGN PRINCIPLE - READ THIS BEFORE MODIFYING ANY CODE

This codebase implements hierarchical RAG (Retrieval-Augmented Generation) with a FUNDAMENTAL PRINCIPLE:

    NEVER LOSE DATA - ALWAYS LET THE LLM DECIDE WHAT'S RELEVANT

What this means in practice:

1. NEVER TRUNCATE DATA
   - Don't take "first N items"
   - Don't cut off text arbitrarily
   - Don't discard chunks randomly

2. NEVER DISCARD DATA WITHOUT LLM SELECTION
   - The LLM must always decide what's relevant
   - If data doesn't fit in the token budget, SPLIT IT SMALLER and ask the LLM to select again
   - Keep iterating: split → LLM selects → check if fits → if not, split smaller and repeat

3. NEVER RAISE EXCEPTIONS WHEN DATA DOESN'T FIT
   - If snippets exceed the token budget, that's not an error - it's a signal to continue navigation
   - Split the data into smaller chunks and let the LLM select again
   - Keep going until the LLM's selection fits within the budget

4. THE NAVIGATION LOOP GUARANTEES FIT
   - navigate_to_code_snippets() ensures returned snippets ALWAYS fit in generate_answer()'s budget
   - It does this by iteratively splitting and re-selecting until the LLM's choices fit
   - This is not optional - it's a guarantee the system provides

5. NEVER FILTER OUT LLM SELECTIONS
   - If the LLM returns invalid URIs, that's a prompt problem, not a data problem
   - Fix the prompt to be clearer about what the LLM should select from
   - Log errors when the LLM doesn't follow instructions, but don't silently discard its choices
   - The only valid reason to filter is if the LLM hallucinated URIs that don't exist anywhere

If you're tempted to truncate, discard, or raise an exception when data doesn't fit:
STOP. You're breaking the fundamental design. Instead, split smaller and ask the LLM to select again.

The LLM is the intelligence that decides what's relevant. Our job is to give it progressively
more granular options until its selection fits the constraints.


CRITICAL ARCHITECTURAL PRINCIPLES FOR PARALLEL OPERATIONS

6. LARGE DATA MUST BE BATCHED, QUEUED, AND PROCESSED IN PARALLEL
   - Don't process large datasets sequentially
   - Batch the data first (e.g., batch_chunks, batch files)
   - Queue all batch operations (transaction_manager.queue)
   - Process queued operations in parallel (process_batches_parallel)
   
7. PARALLEL OPERATIONS MUST BE QUEUED, NOT EXECUTED DIRECTLY
   - Don't use ThreadPoolExecutor directly in operation functions
   - Queue operations at the notebook/workflow level
   - Let the workflow orchestrate parallel execution
   - This ensures caching, consistency, and proper error handling
   
8. LONG-RUNNING OPERATIONS MUST BE DECORATED WITH @transactional
   - Decorate operations with @transactional
   - This enables caching and prevents redundant expensive operations
   - LLM calls, file I/O, and data processing should all be cached
   - Cache invalidation happens automatically based on inputs

Example of CORRECT pattern (see Steps 4-6 in this notebook):
    # Step 1: Batch the data (batch_chunks is decorated with @transactional)
    batches = batch_chunks(chunks=chunks, batch_size=50)
    
    # Step 2: Queue operations for each batch
    for batch in batches:
        transaction_manager.queue(select_chunks, {"question": q, "chunks": batch, ...})
    
    # Step 3: Process queued operations in parallel
    process_batches_parallel(batches, question, depth, model_name, transaction_manager)

Example of INCORRECT pattern (violates principles 7 & 8):
    def select_chunks(chunks):
        # DON'T DO THIS - parallel execution inside the operation
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(process, chunk) for chunk in chunks]
        return results
"""

async def main():
    data_dir = "/Users/ralphus/Development/taskmates-project/taskmates/.taskmates/data"

    input_question = "What files do I need to change to add recipient as a run_opt and force a recipient on a request?"
    input_file_pattern = "*.py"
    input_project_root = "/Users/ralphus/Development/taskmates-project/taskmates/"

    transaction_manager = TransactionManager(cache_dir=data_dir)

    # Complete RAG process using high-level operations
    with runtime.transaction_manager_context(transaction_manager):
        answer_result = await answer_question(
            question=input_question,
            project_root=input_project_root,
            file_pattern=input_file_pattern
        )

        print("\n" + "="*80)
        print("ANSWER:")
        print("="*80)
        print(answer_result['answer'])
        print("\n" + "="*80)
        print("CITATIONS:")
        print("="*80)
        for citation in answer_result['citations']:
            print(f"  - {citation}")


if __name__ == "__main__":
    asyncio.run(main())



