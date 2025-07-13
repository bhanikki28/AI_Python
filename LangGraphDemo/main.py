from typing import Dict, TypedDict
from langgraph.graph import StateGraph

class AgentState(TypedDict):
    message: str
    
def greetingNode(state:AgentState)->AgentState:
    """
    This node prints a greeting message.
    """
    state["message"] = "Hello" + state["message"] + "how is your day going?"
    print(f"Hello {state['message']}")
    return state




def main():
    print("Hello")
    graph = StateGraph(AgentState)
    graph.add_node("greeting", greetingNode)
    graph.set_entry_point("greeting")
    graph.set_finish_point("greeting")
    app = graph.compile()
    app.invoke({"message":"Nikki"})
   
if __name__ == "__main__":
    main()