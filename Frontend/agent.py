"""
Browser-side LangGraph Agent
Runs inside Pyodide (WebAssembly) in the browser.
Uses call_llm() function defined in worker.js to call backend API.
"""

from langgraph.graph import StateGraph, END


def run_graph(user_input: str) -> str:
    """
    Execute the LangGraph agent with the given user input.
    Returns the agent's response as a string.
    
    Graph Structure (matches design doc):
    - decide node: Determines if LLM is needed
    - llm node: Calls backend /llm API via JS bridge
    """
    state = {"input": user_input, "result": "", "need_llm": False}

    graph = StateGraph(dict)

    def decide_node(state):
        """
        Decision node - prepare input and determine next action.
        Matches design doc's decide_node pattern.
        """
        state["need_llm"] = True
        return state

    def llm_node(state):
        """
        LLM node - call backend API via JavaScript bridge.
        call_llm is injected from worker.js.
        """
        # call_llm is defined in worker.js and injected into Python globals
        response = call_llm(state["input"])
        state["result"] = response
        return state

    # Build graph matching design doc structure
    graph.add_node("decide", decide_node)
    graph.add_node("llm", llm_node)

    # Set entry point and edges
    graph.set_entry_point("decide")
    graph.add_edge("decide", "llm")
    graph.add_edge("llm", END)

    # Compile and execute
    app = graph.compile()
    final_state = app.invoke(state)

    return final_state.get("result", "No response generated")
