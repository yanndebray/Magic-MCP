"""
MCP Server Template
"""

# NOTE: This MCP server uses `requests` and `numpy` to call an external MATLAB
# production server and parse the returned matrix. Ensure `requests` and
# `numpy` are installed (they're listed in requirements.txt). To change the
# target MATLAB service, edit the MATLAB_SERVICE_URL variable inside
# `calculate_magic_matrix`.

from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Union

mcp = FastMCP("Echo Server", stateless_http=True)


@mcp.tool(
    title="Echo Tool",
    description="Echo the input text",
)
def echo(text: str = Field(description="The text to echo")) -> str:
    return text

@mcp.tool(title="Magic Matrix", description="Calculate Magic Matrix")
def calculate_magic_matrix(in_param: Union[int, float]) -> dict:
    """Call the external MATLAB service to compute a magic matrix.

    The function sends a JSON payload like {"nargout":1, "rhs": [in_param]}
    to the /mymagic/mymagic endpoint and parses the MATLAB production server
    response into a native Python structure. Returns a dict containing:
      - magic_square: list[list[int]] (rows of the matrix)
      - rows: int
      - cols: int
      - raw: original JSON response (for debugging)
    """
    import json
    import requests
    import numpy as np

    MATLAB_SERVICE_URL = "https://matlab-0j1h.onrender.com"

    # Convert in_param to integer
    try:
        n = int(in_param)
    except (ValueError, TypeError):
        return {"error": f"Invalid parameter: {in_param}. Must be a number."}

    payload = {"nargout": 1, "rhs": [n]}
    headers = {"Content-Type": "application/json"}

    resp = requests.post(f"{MATLAB_SERVICE_URL}/mymagic/mymagic", json=payload, headers=headers, timeout=10)
    resp.raise_for_status()

    j = resp.json()

    # The MATLAB service returns a structure with lhs[0] containing mwdata and mwsize
    try:
        lhs = j.get("lhs", [])[0]
        flat = lhs.get("mwdata")
        rows, cols = lhs.get("mwsize", [None, None])

        if flat is None or rows is None or cols is None:
            # If the response doesn't match expected shape, return raw JSON
            return {"magic_square": None, "rows": None, "cols": None, "raw": j}

        # reshape into nested list for JSON-serializable output
        arr = np.array(flat).reshape(rows, cols)
        magic_list = arr.tolist()

        return {"magic_square": magic_list, "rows": int(rows), "cols": int(cols), "raw": j}
    except Exception as e:
        # Fallback: return raw JSON on any parsing error
        return {"magic_square": None, "rows": None, "cols": None, "raw": j, "error": str(e)}


@mcp.resource(
    uri="greeting://{name}",
    description="Get a personalized greeting",
    name="Greeting Resource",
)
def get_greeting(
    name: str,
) -> str:
    return f"Hello, {name}!"


@mcp.prompt("")
def greet_user(
    name: str = Field(description="The name of the person to greet"),
    style: str = Field(description="The style of the greeting", default="friendly"),
) -> str:
    """Generate a greeting prompt"""
    styles = {
        "friendly": "Please write a warm, friendly greeting",
        "formal": "Please write a formal, professional greeting",
        "casual": "Please write a casual, relaxed greeting",
    }

    return f"{styles.get(style, styles['friendly'])} for someone named {name}."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")