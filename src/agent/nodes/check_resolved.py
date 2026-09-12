from agent.graph_state import CustomAgentState


def check_resolved_agent(state: CustomAgentState) -> bool:
    """Whether the retrieved schema covered the whole request.

    True sends the graph on to SQL generation. False stops it: the unresolved terms have
    nowhere to go yet, and a statement built from a partly-bound request would answer a
    different question from the one asked — dropping a restriction widens the result
    rather than narrowing it, so the answer looks plausible and is wrong.
    """
    return state["schema_ir"]
