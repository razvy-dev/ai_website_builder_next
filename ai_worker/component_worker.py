from typing import TypeDict
from langgraph.graph import StateGraph
from utils.save_file import save_file

class ComponentState(TypeDict):
    component_name: str
    component_code: str
    query_code: str
    typescript_type_code: str
    sanity_schema_code: str


def design_component(state: ComponentState) -> ComponentState:
    """This node is in charge of designing the next.js component"""
    pass

def save_component(state: ComponentState) -> ComponentState:
    """This node is in charge of saving the next.js component"""
    try:
        save_file("./components", state["component_code"], f"{state['component_name']}", "tsx")

        # i could save the path in the db so reconstructing this afterwards is easy

    except Exception as e:
        print(f"Error saving component: {e}")
    pass

def design_query(state: ComponentState) -> ComponentState:
    """This node is in charge of designing the query for the component"""
    pass

def save_query(state: ComponentState) -> ComponentState:
    """This node is in charge of saving the query for the component"""
    try:
        save_file("./queries", state["query_code"], f"{state['component_name']}", "ts")

        # i could save the path in the db so reconstructing this afterwards is easy

    except Exception as e:
        print(f"Error saving query: {e}")
    pass

def design_typescript_type(state: ComponentState) -> ComponentState:
    """This node is in charge of designing the typescript type for the component"""
    pass

def save_typescript_type(state: ComponentState) -> ComponentState:
    """This node is in charge of saving the typescript type for the component"""
    try:
        save_file("./types", state["typescript_type_code"], f"{state['component_name']}", "ts")
        # i could save the path in the db so reconstructing this afterwards is easy
    except Exception as e:
        print(f"Error saving typescript type: {e}")
    pass

def design_sanity_schema(state: ComponentState) -> ComponentState:
    """This node is in charge of designing the sanity schema for the component"""
    pass

def save_sanity_schema(state: ComponentState) -> ComponentState:
    """This node is in charge of saving the sanity schema for the component"""
    try:
        save_file("./schemas", state["sanity_schema_code"], f"{state['component_name']}", "ts")
        # i could save the path in the db so reconstructing this afterwards is easy
    except Exception as e:
        print(f"Error saving sanity schema: {e}")
    pass

graph = StateGraph(ComponentState)

# we first need to dregister all nodes

graph.add_node("design_sanity_schema", design_sanity_schema)
graph.add_node("save_sanity_schema", save_sanity_schema)
graph.add_node("design_query", design_query)
graph.add_node("save_query", save_query)
graph.add_node("design_typescript_type", design_typescript_type)
graph.add_node("save_typescript_type", save_typescript_type)
graph.add_node("design_component", design_component)
graph.add_node("save_component", save_component)

# now, the steps:

graph.add_edge("save_typescript_type", "design_sanity_schema")
graph.add_edge("design_sanity_schema", "save_sanity_schema")
graph.add_edge("save_component", "design_query")
graph.add_edge("design_query", "save_query")
graph.add_edge("save_query", "design_typescript_type")
graph.add_edge("design_typescript_type", "save_typescript_type")
graph.add_edge("save_typescript_type", "design_component")
graph.add_edge("design_component", "save_component")


app = graph.compile()

result = app.invoke({"component_name": "bob"})
print(result)

# so I am guessing my state would be made of what I know about a component
# and each node will be what I need to do about it: design the next.js component, add the query for it, typescript type, add it in sanity and add the data from figma into it
# after this is done, i need to: assemble the everything, make sure it works and start working on the design. that would mean invoking nodes with validation logic such as playwright, preceptual hashes and all that kind of stuff