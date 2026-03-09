from __future__ import annotations

from nessie_api.models import (
    Action,
    plugin,
    Graph,
    Node,
    FilterExpression,
    FilterOperator,
    Workspace
)


# ─────────────────────────────────────────────
#  Core filtering logic
# ─────────────────────────────────────────────

def _node_matches_filter(node: Node, f: FilterExpression) -> bool:
    attr = node.get_attribute(f.attr_name)
    if attr is None:
        return False

    a, b = attr.value, f.value

    if type(a) is not type(b):
        raise TypeError(
            f"Type mismatch on node {node.id!r}: "
            f"attribute '{f.attr_name}' is {type(a).__name__}, "
            f"filter value is {type(b).__name__}."
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


def apply_filters(graph: Graph, filters: list[FilterExpression]) -> Graph:
    """
    Applies all active filters sequentially on the graph.
    Each filter narrows down the result of the previous one.
    Returns a subgraph containing only matching nodes and edges between them.
    """
    matched_ids = {node.id for node in graph.nodes}

    for f in filters:
        matched_ids = {
            node_id for node_id in matched_ids
            if _node_matches_filter(graph.get_node(node_id), f)
        }

    return _build_subgraph(graph, matched_ids)


def apply_search(graph: Graph, query: str) -> Graph:
    """
    Filters graph nodes by free-text search across all attribute names and values.
    Returns a subgraph containing only matching nodes and edges between them.
    """
    matched_ids = {
        node.id for node in graph.nodes
        if _node_matches_search(node, query)
    }
    return _build_subgraph(graph, matched_ids)


def _build_subgraph(source: Graph, node_ids: set[str]) -> Graph:
    sub = Graph(source.graph_type)
    for nid in node_ids:
        sub.add_node(source.get_node(nid))
    for edge in source.edges:
        if edge.source.id in node_ids and edge.target.id in node_ids:
            sub.add_edge(edge)
    return sub


# ─────────────────────────────────────────────
#  Handlers
#
#  Every handler receives an Action whose payload
#  is a dict with at least {"workspace": Workspace}
#  plus any handler-specific keys documented below.
# ─────────────────────────────────────────────

def _handle_filter(action: Action) -> Graph:
    """
    payload: {
        "workspace": Workspace,
        "filter": str | FilterExpression   # the new filter to add
    }

    Parses the filter if needed, adds it to the workspace,
    and returns the filtered subgraph.
    """
    workspace: Workspace = action.payload["workspace"]
    raw = action.payload["filter"]

    if isinstance(raw, str):
        expr = FilterExpression.from_string(raw)
    elif isinstance(raw, FilterExpression):
        expr = raw
    else:
        raise TypeError(f"'filter' must be str or FilterExpression, got {type(raw)}.")

    workspace.add_filter(expr)
    return apply_filters(workspace.source_graph, workspace.active_filters)


def _handle_search(action: Action) -> Graph:
    """
    payload: {
        "workspace": Workspace,
        "query": str
    }

    Applies active workspace filters first, then narrows
    the result further by free-text search.
    Search is not saved to workspace state (non-persistent).
    """
    workspace: Workspace = action.payload["workspace"]
    query: str = action.payload["query"]

    filtered = apply_filters(workspace.source_graph, workspace.active_filters)
    if not query or not query.strip():
        return filtered

    return apply_search(filtered, query)


def _handle_undo(action: Action) -> Graph:
    """
    payload: {"workspace": Workspace}

    Undoes the last filter operation and returns the updated subgraph.
    """
    workspace: Workspace = action.payload["workspace"]
    workspace.undo()
    return apply_filters(workspace.source_graph, workspace.active_filters)


def _handle_redo(action: Action) -> Graph:
    """
    payload: {"workspace": Workspace}

    Redoes the last undone filter operation and returns the updated subgraph.
    """
    workspace: Workspace = action.payload["workspace"]
    workspace.redo()
    return apply_filters(workspace.source_graph, workspace.active_filters)


def _handle_reset(action: Action) -> Graph:
    """
    payload: {"workspace": Workspace}

    Clears all active filters and returns the original source graph.
    """
    workspace: Workspace = action.payload["workspace"]
    workspace.clear_filters()
    return workspace.source_graph


# ─────────────────────────────────────────────
#  Plugin definition
# ─────────────────────────────────────────────

@plugin(name="GraphManipulationPlugin")
def graph_manipulation_plugin():
    handlers = {
        "filter": _handle_filter,
        "search": _handle_search,
        "undo":   _handle_undo,
        "redo":   _handle_redo,
        "reset":  _handle_reset,
    }
    requires = []
    return handlers, requires
