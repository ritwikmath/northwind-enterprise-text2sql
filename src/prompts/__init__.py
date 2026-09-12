from functools import cache

from paths import PROMPTS_DIR


@cache
def get_prompt(agent_name: str) -> str:
    file_path = PROMPTS_DIR / f"{agent_name}.txt"

    with open(file_path, "r") as file:
        return file.read()