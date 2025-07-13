from typing import TypedDict,Dict
from langgraph.graph import StateGraph
from functools import reduce


def main():
    print("Demo for processing the list using nodes")

class AgentState(TypedDict):
    skills_list: list[str]
    name: str
    age: int
    final: str

def first_node(state:AgentState)->AgentState:
    """ This is the first node that will set the name to the state """
    state["final"] = f"Hi , {state["name"]}" +"!"
    return state

def second_node(state:AgentState)->AgentState:
    """ This is the second node for setting up the age in the state"""
    state["final"] = state["final"] +f" you are {state["age"]} years old!"
    return state

def third_node(state:AgentState)->AgentState:
    """ This is the third node for setting up the age in the state"""
    state["final"] = state["final"] +f" you got skills in {get_skills(state["skills_list"])}"
    return state

def get_skills(skills_list):
    result = ""
    for skill in skills_list:
        result += skill +","
    return result

if __name__ == "__main__":
    graph = StateGraph(AgentState)
    graph.add_node("first_node", first_node)
    graph.add_node("second_node", second_node)
    graph.add_node("third_node", third_node)
    graph.add_edge("first_node","second_node")
    graph.add_edge("second_node","third_node")
    graph.set_entry_point("first_node")
    graph.set_finish_point("third_node")

    app = graph.compile()
    response =app.invoke({"name": "Nikki", "age":14, "skills_list":["Python", "Java", "AI"]})
    print(response["final"])
    main