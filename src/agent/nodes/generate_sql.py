from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from agent.graph_state import CustomAgentState
from llm import sql_spec
from llm.sql_guard import UnsafeSQL, verify
from llm.structured_output.sql_generate import PreparedStatement, SQLQuery
from prompts import get_prompt


def generate_sql_agent(state: CustomAgentState):
    """Write the statement for a query whose columns are already settled.

    The conversation is not carried into this step. The IR is the entire request by the
    time it gets here, and the user's original words can only reintroduce what the
    earlier stages spent their work removing — a term that resolved to nothing, a value
    that belongs in a parameter. So the model is given the specification alone.
    """
    specification = sql_spec.build(state["sql_query_ir"])

    system_prompt = PromptTemplate.from_template(get_prompt("sql_generate")).format(
        sql_specification=specification.text
    )

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    current_agent = create_agent(
        model=model,
        system_prompt=system_prompt,
        response_format=SQLQuery,
    )

    response = current_agent.invoke(
        {"messages": [HumanMessage("Finish the statement in the specification.")]}
    )

    try:
        sql = verify(response["structured_response"].sql, specification.placeholders)
    except UnsafeSQL as rejection:
        # The statement is discarded, not repaired: nothing here can tell a model that
        # misread the spec from one that was talked into ignoring it.
        return {
            "prepared_statement": None,
            "sql_error": str(rejection),
        }

    return {
        "prepared_statement": PreparedStatement(
            sql=sql,
            parameters=specification.parameters,
            omitted=specification.omitted,
        ),
        "sql_error": None,
    }
