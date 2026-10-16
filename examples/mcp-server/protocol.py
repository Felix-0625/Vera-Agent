"""JSON-RPC 2.0 protocol structures for the MCP stdio server.

This module defines the wire-level data structures used by the server:
requests, responses, error objects, and the standard MCP error codes.

The structures are intentionally lightweight (dataclasses over ``dict``) so the
container can be emitted straight onto stdout via :mod:`json`, while still
offering typed construction helpers for the rest of the codebase.

Reference: https://www.jsonrpc.org/specification
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

__all__ = [
    "JSONRPC_VERSION",
    "PARSE_ERROR",
    "INVALID_REQUEST",
    "METHOD_NOT_FOUND",
    "INVALID_PARAMS",
    "INTERNAL_ERROR",
    "ErrorObject",
    "Request",
    "Response",
    "Notification",
    "MethodNotFound",
    "make_error_response",
    "make_result_response",
]

JSONRPC_VERSION = "2.0"

# ---------------------------------------------------------------------------
# Standard JSON-RPC 2.0 error codes
# ---------------------------------------------------------------------------
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# MCP reserves the -32000..-32099 range for server defined errors.
SERVER_ERROR = -32000

# A JSON-RPC id may be a string, a number or null. ``None`` acts as the
# "absent / notification" sentinel here.
JSONRPCId = Optional[Union[str, int]]


class MethodNotFound(Exception):
    """Raised by a dispatcher when a method has no registered handler."""


@dataclass
class ErrorObject:
    """A JSON-RPC 2.0 error object."""

    code: int
    message: str
    data: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain ``dict``, omitting ``data`` when unset."""
        payload: Dict[str, Any] = {"code": self.code, "message": self.message}
        if self.data is not None:
            payload["data"] = self.data
        return payload


@dataclass
class Request:
    """An incoming JSON-RPC 2.0 request or notification.

    ``id`` is ``None`` when the message is a notification (no response is
    expected by the peer).
    """

    method: str
    params: Dict[str, Any] = field(default_factory=dict)
    id: JSONRPCId = None
    jsonrpc: str = JSONRPC_VERSION

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Request":
        """Build a :class:`Request` from a decoded JSON object.

        Raises:
            ValueError: if the payload is not a structurally valid request.
        """
        if not isinstance(payload, dict):
            raise ValueError("request must be a JSON object")

        method = payload.get("method")
        if not isinstance(method, str) or not method:
            raise ValueError("request 'method' must be a non-empty string")

        params = payload.get("params", {})
        if params is None:
            params = {}
        if not isinstance(params, (dict, list)):
            raise ValueError("request 'params' must be an object or array")

        raw_id = payload.get("id")
        if raw_id is not None and not isinstance(raw_id, (str, int, bool)):
            raise ValueError("request 'id' must be a string, number or null")

        return cls(
            method=method,
            params=params,
            id=raw_id,
            jsonrpc=payload.get("jsonrpc", JSONRPC_VERSION),
        )

    @property
    def is_notification(self) -> bool:
        """``True`` when the peer expects no response (id is absent)."""
        return self.id is None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
        }
        if self.params:
            payload["params"] = self.params
        if self.id is not None:
            payload["id"] = self.id
        return payload


@dataclass
class Response:
    """A JSON-RPC 2.0 response (either ``result`` or ``error``)."""

    id: JSONRPCId = None
    result: Optional[Any] = None
    error: Optional[ErrorObject] = None
    jsonrpc: str = JSONRPC_VERSION

    def __post_init__(self) -> None:
        if self.result is not None and self.error is not None:
            raise ValueError("response cannot carry both 'result' and 'error'")

    def to_dict(self) -> Dict[str, Any]:
        """Serialise into the exact JSON-RPC 2.0 wire shape."""
        payload: Dict[str, Any] = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error is not None:
            payload["error"] = self.error.to_dict()
        else:
            # ``result`` is REQUIRED on success, even when it is null.
            payload["result"] = self.result
        return payload

    def to_json(self) -> str:
        """Encode as a single-line JSON string (no embedded newlines)."""
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))


@dataclass
class Notification:
    """An outgoing JSON-RPC 2.0 notification (no id, no response expected)."""

    method: str
    params: Dict[str, Any] = field(default_factory=dict)
    jsonrpc: str = JSONRPC_VERSION

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"jsonrpc": self.jsonrpc, "method": self.method}
        if self.params:
            payload["params"] = self.params
        return payload


def make_error_response(
    request_id: JSONRPCId,
    code: int,
    message: str,
    data: Optional[Any] = None,
) -> Response:
    """Convenience factory for an error :class:`Response`."""
    return Response(id=request_id, error=ErrorObject(code=code, message=message, data=data))


def make_result_response(request_id: JSONRPCId, result: Any) -> Response:
    """Convenience factory for a successful :class:`Response`."""
    return Response(id=request_id, result=result)
