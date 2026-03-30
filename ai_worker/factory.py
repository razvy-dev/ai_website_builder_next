from typing import Dict, TypeDict
from langgraph.graph import StateGraph

class FactoryState(TypeDict):
    website: str

def greeting_node(state: FactoryState) -> FactoryState:
    """
    Greeting node for the factory.
    
    Args:
        state: The current state of the graph
        
    Returns:
        The updated state with a greeting website
    """
    state["website"] = "Hello World" + state["website"]
    return state

graph = StateGraph(FactoryState)

graph.add_node("greeting", greeting_node)

graph.set_entry_point("greeting")
graph.set_finish_point("greeting")

app = graph.compile()

result = app.invoke({"website": "bob"})
print(result)