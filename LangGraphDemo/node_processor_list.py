from typing import TypedDict,Dict
from langgraph.graph import StateGraph
from functools import reduce


def main():
    print("Demo for processing the list using nodes")

class AgentState(TypedDict):
    list_data: list[int]
    name: str
    result: str


def total(num_list):
    total = sum(num_list)
    print(total)
    return total

def node_processor_1(state: AgentState) -> AgentState:
    state["result"] = "Hello " + state["name"] + " :your total sum is :" + str(  total(state["list_data"]))
    return state


if __name__ == "__main__":
    graph = StateGraph(AgentState)
    graph.add_node("node_processor_1", node_processor_1)
    graph.set_entry_point("node_processor_1")
    graph.set_finish_point("node_processor_1")
    app = graph.compile()
    response =app.invoke({"list_data": [1, 2, 3, 4, 5], "name": "Nikki"})
    print(response["result"])
    main