from typing import TypedDict,Dict
from langgraph.graph import StateGraph,START,END
from functools import reduce


def main():
    print("Demo for router nodes and conditional edges")

class AgentState(TypedDict):
   first_number: int
   second_number: int
   result: int
   operation: str

def adder_node(state:AgentState)->AgentState:
    """ This is the adder node that will add the two numbers """
    state["result"] = state["first_number"] + state["second_number"]
    return state

def subtractor_node(state:AgentState)->AgentState:
    """ This is the subtractor node that will subtract the two numbers """
    state["result"] = state["first_number"] - state["second_number"]
    return state

def multiplier_node(state:AgentState)->AgentState:
    """ This is the multiplier node that will multiply the two numbers """
    state["result"] = state["first_number"] * state["second_number"]
    return state

def decider_node(state:AgentState)->AgentState:
    """ This is the decider node that will decide the operation to be performed """
    if state["operation"] == "add":
        return "adder_node"
    elif state["operation"] == "subtract":
        return "subtractor_node"    
    elif state["operation"] == "multiply":
        return "multiplier_node"
    else:
        return "adder_node"




if __name__ == "__main__":
    graph = StateGraph(AgentState)
    graph.add_node("adder_node", adder_node)
    graph.add_node("subtractor_node", subtractor_node)
    graph.add_node("multiplier_node", multiplier_node)
    graph.add_node("router", lambda state:state) #passthrough function
    graph.add_edge(START,"router")
    graph.add_conditional_edges("router",decider_node,{"adder_node":"adder_node",
                                                    "subtractor_node":"subtractor_node",
                                                    "multiplier_node":"multiplier_node"})
    graph.add_edge("adder_node",END)
    graph.add_edge("subtractor_node",END)
    

    app = graph.compile()
    response =app.invoke({"first_number":10,"second_number":20,"operation":"add"})
    print(response["result"])
    main