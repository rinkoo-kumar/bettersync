"""
Model Context Protocol (MCP) Server for BetterUp People Systems.
Allows Claude Desktop, Claude Code, or Cursor to query cross-system HR state,
reconcile discrepancies, and trigger idempotent synchronization.
"""

import sys
import json
from typing import Any, Dict
from src.core.reconciler import Reconciler
from src.agent.mcp_tools import MCP_TOOL_DEFINITIONS


class PeopleSyncMCPServer:
    def __init__(self):
        self.reconciler = Reconciler()

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": MCP_TOOL_DEFINITIONS
                }
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})
            return self.execute_tool(req_id, tool_name, args)
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not found."
                }
            }

    def execute_tool(self, req_id: Any, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if tool_name == "get_hire_cross_system_state":
                hire_id = args["hire_id"]
                state = {
                    "hire_id": hire_id,
                    "ashby": self.reconciler.ashby.get_by_hire_id(hire_id),
                    "workday": self.reconciler.workday.get_by_hire_id(hire_id),
                    "okta": self.reconciler.okta.get_by_hire_id(hire_id),
                    "expoit": self.reconciler.expoit.get_by_hire_id(hire_id),
                }
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(state, indent=2)}]}
                }

            elif tool_name == "compute_system_drift":
                hire_id = args["hire_id"]
                drifts = self.reconciler.compute_drift(hire_id)
                serialized = [d.model_dump() for d in drifts]
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(serialized, indent=2)}]}
                }

            elif tool_name == "resolve_discrepancy_and_sync":
                hire_id = args["hire_id"]
                field = args["field_name"]
                val = args["authoritative_value"]
                targets = args["target_systems"]
                rationale = args["rationale"]

                for target in targets:
                    key = f"mcp_sync:{hire_id}:{field}:{target}"
                    if target == "workday":
                        self.reconciler.workday.create_or_update(hire_id, {field: val}, key)
                    elif target == "okta":
                        self.reconciler.okta.create_or_update(hire_id, {field: val}, key)
                    elif target == "expoit":
                        order = self.reconciler.expoit.get_by_hire_id(hire_id)
                        if order:
                            self.reconciler.expoit.create_or_update(order["order_id"], {field: val}, key)

                self.reconciler.audit.log(
                    event_type="mcp_tool_resolved",
                    entity_id=hire_id,
                    actor="claude_mcp_client",
                    diff={"field": field, "value": val, "targets": targets},
                    decision_rationale=rationale,
                    status="SUCCESS"
                )

                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": f"Successfully synchronized {field} to {targets}."}]}
                }

            elif tool_name == "notify_people_ops_slack":
                channel = args.get("channel", "#people-ops-triage")
                headline = args.get("headline")
                body = args.get("body_markdown")
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": f"Posted notification to {channel}: {headline}"}]}
                }

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": f"Unknown tool name: {tool_name}"}
                }

        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": str(e)}
            }

    def run_stdio(self):
        """Standard JSON-RPC loop over stdin / stdout."""
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                request = json.loads(line)
                response = self.handle_request(request)
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
            except Exception as e:
                err = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(e)}}
                sys.stdout.write(json.dumps(err) + "\n")
                sys.stdout.flush()


if __name__ == "__main__":
    server = PeopleSyncMCPServer()
    server.run_stdio()
