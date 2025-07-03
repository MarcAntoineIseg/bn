from fastapi import FastAPI
from ga4_tool import mcp

# Get MCP's ASGI-compatible app
mcp_app = mcp.http_app(path="/mcp")

# Create FastAPI and mount MCP under "/mcp-server"
app = FastAPI(lifespan=mcp_app.lifespan)  # ⚠️ VERY IMPORTANT
app.mount("/mcp-server", mcp_app)
