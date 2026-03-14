from __future__ import annotations

from nessie_api.models import (
    Action,
    plugin,
    Graph,
    Node,
    FilterExpression,
    FilterOperator,
)
from nessie_api.protocols import Context


# ─────────────────────────────────────────────
#  Core filtering logic
# ─────────────────────────────────────────────

def _node_matches_filter(node: Node, f: FilterExpression) -> bool:
    attr = node.get_attribute(f.attr_name)
    if attr is None:
        return False

    a, b = attr.value, f.value

    if type(a) is not type(b):
        try:
            b = type(a)(b)
        except (ValueError, TypeError):
            raise TypeError(
                f"Type mismatch on node {node.id!r}: "
                f"attribute '{f.attr_name}' is {type(a).__name__}, "
                f"filter value is {type(b).__name__} and cannot be converted."
            )

    match f.operator:
        case FilterOperator.EQ: return a == b
        case FilterOperator.NEQ: return a != b
        case FilterOperator.LT: return a < b
        case FilterOperator.LTE: return a <= b
        case FilterOperator.GT: return a > b
        case FilterOperator.GTE: return a >= b


def _node_matches_search(node: Node, query: str) -> bool:
    q = query.lower()
    return any(
        q in attr.name.lower() or q in str(attr.value).lower()
        for attr in node.attributes.values()
    )


def _build_subgraph(source: Graph, node_ids: set[str]) -> Graph:
    sub = Graph(source.name, source.graph_type)
    for nid in node_ids:
        sub.add_node(source.get_node(nid))
    for edge in source.edges:
        if edge.source.id in node_ids and edge.target.id in node_ids:
            sub.add_edge(edge)
    return sub


def _apply(graph: Graph, filters: list[FilterExpression], search: str) -> Graph:
    """Shared core: apply filters then search on a graph."""
    matched_ids = {node.id for node in graph.nodes}

    for f in filters:
        matched_ids = {
            nid for nid in matched_ids
            if _node_matches_filter(graph.get_node(nid), f)
        }

    if search and search.strip():
        matched_ids = {
            nid for nid in matched_ids
            if _node_matches_search(graph.get_node(nid), search)
        }

    return _build_subgraph(graph, matched_ids)


# ─────────────────────────────────────────────
#  Handlers
# ─────────────────────────────────────────────

def _handle_filter_graph(action: Action, context: Context) -> Graph:
    """
    payload: {
        "graph":   Graph,
        "filters": list[FilterExpression],
        "search":  str
    }
    """
    return _apply(
        action.payload["graph"],
        action.payload.get("filters", []),
        action.payload.get("search", ""),
    )


def _handle_undo(action: Action, context: Context) -> Graph | None:
    """
    Undoes the last filter operation on the active workspace
    and returns the updated subgraph.
    """
    index = context.get_active_workspace_index()
    if index is None:
        return

    context.undo_at(index)
    return _apply(
        context.get_full_graph_at(index),
        context.get_active_filters_at(index),
        context.get_search_at(index) or "",
    )


def _handle_redo(action: Action, context: Context) -> Graph | None:
    """
    Redoes the last undone filter operation on the active workspace
    and returns the updated subgraph.
    """
    index = context.get_active_workspace_index()
    if index is None:
        return

    context.redo_at(index)
    return _apply(
        context.get_full_graph_at(index),
        context.get_active_filters_at(index),
        context.get_search_at(index) or "",
    )


def _handle_reset(action: Action, context: Context) -> Graph | None:
    """
    Clears all filters and search on the active workspace
    and returns the full source graph.
    """
    index = context.get_active_workspace_index()
    if index is None:
        return

    context.clear_filters_at(index)
    context.set_search_at(index, "")
    return context.get_full_graph_at(index)


# ─────────────────────────────────────────────
#  Plugin definition
# ─────────────────────────────────────────────

@plugin(name="GraphManipulationPlugin")
def graph_manipulation_plugin():
    handlers = {
        "filter_graph": _handle_filter_graph,
        "undo":         _handle_undo,
        "redo":         _handle_redo,
        "reset":        _handle_reset,
    }
    requires = []
    setup_requires = {}

    return {
        "handlers": handlers,
        "requires": requires,
        "setup_requires": setup_requires,
    }
