# nessie-graph-manipulation-plugin

A [Nessie](https://github.com/Nessie-org) plugin for **filtering and searching graphs** — narrow any graph down to a subgraph by applying attribute-based filter expressions, a free-text search, or both at once.

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-orange)](https://pypi.org/project/nessie-graph-manipulation-plugin/)

---

## Overview

This plugin operates on an already-loaded Nessie `Graph` object and returns a filtered subgraph. It:

- Applies one or more **`FilterExpression`** rules against node attributes (e.g. `salary > 50000`, `status == "active"`)
- Optionally runs a **free-text search** across all attribute names and values
- Filters are applied **in order** — each step narrows down the surviving nodes
- Retains only the **edges whose both endpoints** are still in the subgraph
- Registers automatically with the Nessie plugin system via a Python entry point

---

## Requirements

- Python 3.9 or higher
- [`nessie-api`](https://github.com/Nessie-org) >= 0.1.0

---

## Installation

```bash
pip install nessie-graph-manipulation-plugin
```

Or install from source:

```bash
git clone https://github.com/Nessie-org/nessie-graph-manipulation-plugin.git
cd nessie-graph-manipulation-plugin
pip install -e .
```

---

## Usage

### Via the Nessie plugin system

The plugin registers itself under the name `"GraphManipulationPlugin"` and is automatically discovered by Nessie through the `nessie_plugins` entry point.

```python
from nessie_graph_manipulation_plugin import graph_manipulation_plugin
from nessie_api.models import Action, FilterExpression, FilterOperator

plugin = graph_manipulation_plugin()

subgraph = plugin.handle(
    Action("filter_graph", {
        "graph":   my_graph,                         # a nessie_api Graph object
        "filters": [
            FilterExpression("salary", FilterOperator.GT, 50000),
            FilterExpression("status", FilterOperator.EQ, "active"),
        ],
        "search": "engineering",                     # optional free-text search
    }),
    context=None,
)

print(subgraph)
```

---

## Handlers

### `filter_graph`

Filters nodes in a graph by attribute expressions and/or a search query, then returns a subgraph containing only the matching nodes and the edges between them.

**Payload fields:**

| Field     | Type                      | Required | Description                                                  |
|-----------|---------------------------|----------|--------------------------------------------------------------|
| `graph`   | `Graph`                   | Yes      | The source Nessie graph to filter                            |
| `filters` | `list[FilterExpression]`  | No       | Attribute filter rules (default: `[]`, no filtering)         |
| `search`  | `str`                     | No       | Free-text query matched against attribute names and values   |

---

## FilterExpression

A `FilterExpression` describes a single attribute-level condition:

```python
FilterExpression(attr_name: str, operator: FilterOperator, value: Any)
```

### Supported operators

| Operator              | Symbol | Example                                           |
|-----------------------|--------|---------------------------------------------------|
| `FilterOperator.EQ`   | `==`   | `FilterExpression("status", EQ, "active")`        |
| `FilterOperator.NEQ`  | `!=`   | `FilterExpression("role", NEQ, "intern")`         |
| `FilterOperator.LT`   | `<`    | `FilterExpression("age", LT, 30)`                 |
| `FilterOperator.LTE`  | `<=`   | `FilterExpression("score", LTE, 100)`             |
| `FilterOperator.GT`   | `>`    | `FilterExpression("salary", GT, 50000)`           |
| `FilterOperator.GTE`  | `>=`   | `FilterExpression("priority", GTE, 2)`            |

### Type coercion

If the filter value type does not match the stored attribute type, the plugin attempts to coerce the filter value to match. If coercion fails, a `TypeError` is raised with a descriptive message including the node ID and attribute name.

---

## Free-text search

When a `search` string is provided, a node is retained only if the query (case-insensitive) appears in **any** attribute name or attribute value. This runs after all `filters` have been applied.

```python
# Keep only nodes that match the filters AND contain "python" somewhere
Action("filter_graph", {
    "graph": my_graph,
    "filters": [FilterExpression("level", FilterOperator.EQ, "advanced")],
    "search": "python",
})
```

---

## How the subgraph is built

1. Start with the set of all node IDs in the source graph.
2. Apply each `FilterExpression` in order — each one narrows the set.
3. If a non-empty `search` string is given, narrow the set further.
4. Copy all surviving nodes into a new `Graph` with the same name and graph type.
5. Copy all edges from the source graph whose **source and target** are both in the surviving set.

---

## Examples

### Filter by a single attribute

```python
from nessie_api.models import Action, FilterExpression, FilterOperator
from nessie_graph_manipulation_plugin import graph_manipulation_plugin

plugin = graph_manipulation_plugin()

# Keep only nodes where _table == "employees"
result = plugin.handle(
    Action("filter_graph", {
        "graph": graph,
        "filters": [FilterExpression("_table", FilterOperator.EQ, "employees")],
    }),
    context=None,
)
```

### Chain multiple filters

```python
# Employees in department 3 earning more than 70 000
result = plugin.handle(
    Action("filter_graph", {
        "graph": graph,
        "filters": [
            FilterExpression("_table",        FilterOperator.EQ,  "employees"),
            FilterExpression("department_id", FilterOperator.EQ,  3),
            FilterExpression("salary",        FilterOperator.GT,  70000),
        ],
    }),
    context=None,
)
```

### Search only (no attribute filters)

```python
# All nodes that mention "devops" anywhere in their attributes
result = plugin.handle(
    Action("filter_graph", {
        "graph": graph,
        "search": "devops",
    }),
    context=None,
)
```

### Combined filter + search

```python
# Active projects that reference "backend"
result = plugin.handle(
    Action("filter_graph", {
        "graph": graph,
        "filters": [FilterExpression("status", FilterOperator.EQ, "active")],
        "search": "backend",
    }),
    context=None,
)
```

---

## Development

### Setting up a local environment

```bash
git clone https://github.com/Nessie-org/nessie-graph-manipulation-plugin.git
cd nessie-graph-manipulation-plugin
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

---

## Project structure

```
nessie-graph-manipulation-plugin/
├── src/
│   └── nessie_graph_manipulation_plugin/
│       ├── __init__.py                    # Exports graph_manipulation_plugin
│       └── graph_manipulation_plugin.py   # Core plugin logic
├── pyproject.toml
└── README.md
```

---

## Author

**Stefan Ilić** — [stefanilic3001@gmail.com](mailto:stefanilic3001@gmail.com)

Issues and contributions welcome at the [GitHub repository](https://github.com/Nessie-org/nessie-graph-manipulation-plugin/issues).