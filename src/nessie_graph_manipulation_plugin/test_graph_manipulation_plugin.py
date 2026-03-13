import unittest

from nessie_api.models import (
    Graph,
    Node,
    Attribute,
    Workspace,
    Action,
    GraphType,
    FilterExpression,
)

from .graph_manipulation_plugin import graph_manipulation_plugin


class TestGraphManipulationPlugin(unittest.TestCase):

    def setUp(self):
        self.graph = Graph("a", GraphType.DIRECTED)

        self.n1 = Node("1")
        self.n1.add_attribute(Attribute("age", 25))
        self.n1.add_attribute(Attribute("name", "Alice"))

        self.n2 = Node("2")
        self.n2.add_attribute(Attribute("age", 35))
        self.n2.add_attribute(Attribute("name", "Bob"))

        self.n3 = Node("3")
        self.n3.add_attribute(Attribute("age", 40))
        self.n3.add_attribute(Attribute("name", "Charlie"))

        self.graph.add_node(self.n1)
        self.graph.add_node(self.n2)
        self.graph.add_node(self.n3)

        self.workspace = Workspace(self.graph)

        plugin = graph_manipulation_plugin()
        self.handlers = plugin.handlers

    def _filter_action(self, filter_str: str) -> Action:
        return Action("filter_graph", {
            "graph": self.workspace.source_graph,
            "filters": self.workspace.active_filters,
            "search": "",
        })

    def _apply(self, search: str = "") -> Action:
        return Action("filter_graph", {
            "graph": self.workspace.source_graph,
            "filters": self.workspace.active_filters,
            "search": search,
        })

    # ---------------------------
    # BASIC FUNCTIONALITY
    # ---------------------------

    def test_filter_basic(self):
        self.workspace.add_filter(FilterExpression.from_string("age > 30"))

        result = self.handlers["filter_graph"](self._apply())

        ids = {n.id for n in result.nodes}
        self.assertEqual(ids, {"2", "3"})

    def test_search_basic(self):
        result = self.handlers["filter_graph"](self._apply(search="bob"))

        ids = {n.id for n in result.nodes}
        self.assertEqual(ids, {"2"})

    # ---------------------------
    # FILTER EDGE CASES
    # ---------------------------

    def test_filter_no_results(self):
        self.workspace.add_filter(FilterExpression.from_string("age > 100"))

        result = self.handlers["filter_graph"](self._apply())
        self.assertEqual(len(result.nodes), 0)

    def test_filter_missing_attribute(self):
        self.workspace.add_filter(FilterExpression.from_string("salary > 1000"))

        result = self.handlers["filter_graph"](self._apply())
        self.assertEqual(len(result.nodes), 0)

    def test_filter_type_mismatch(self):
        self.workspace.add_filter(FilterExpression.from_string('age == "Alice"'))

        with self.assertRaises(TypeError):
            self.handlers["filter_graph"](self._apply())

    def test_multiple_filters(self):
        self.workspace.add_filter(FilterExpression.from_string("age > 20"))
        self.workspace.add_filter(FilterExpression.from_string("age < 40"))

        result = self.handlers["filter_graph"](self._apply())

        ids = {n.id for n in result.nodes}
        self.assertEqual(ids, {"1", "2"})

    # ---------------------------
    # SEARCH EDGE CASES
    # ---------------------------

    def test_search_case_insensitive(self):
        result = self.handlers["filter_graph"](self._apply(search="ALICE"))

        ids = {n.id for n in result.nodes}
        self.assertEqual(ids, {"1"})

    def test_search_empty_query(self):
        result = self.handlers["filter_graph"](self._apply(search=""))

        self.assertEqual(len(result.nodes), 3)

    def test_search_no_match(self):
        result = self.handlers["filter_graph"](self._apply(search="zzz"))

        self.assertEqual(len(result.nodes), 0)

    # ---------------------------
    # UNDO / REDO
    # ---------------------------

    def test_undo(self):
        self.workspace.add_filter(FilterExpression.from_string("age > 30"))

        self.workspace.undo()
        result = self.handlers["filter_graph"](self._apply())

        ids = {n.id for n in result.nodes}
        self.assertEqual(ids, {"1", "2", "3"})

    def test_redo(self):
        self.workspace.add_filter(FilterExpression.from_string("age > 30"))
        self.workspace.undo()
        self.workspace.redo()

        result = self.handlers["filter_graph"](self._apply())

        ids = {n.id for n in result.nodes}
        self.assertEqual(ids, {"2", "3"})

    def test_undo_without_history(self):
        self.workspace.undo()  # no-op
        result = self.handlers["filter_graph"](self._apply())

        self.assertEqual(len(result.nodes), 3)

    # ---------------------------
    # RESET
    # ---------------------------

    def test_reset(self):
        self.workspace.add_filter(FilterExpression.from_string("age > 30"))
        self.workspace.clear_filters()

        result = self.handlers["filter_graph"](self._apply())

        ids = {n.id for n in result.nodes}
        self.assertEqual(ids, {"1", "2", "3"})

    # ---------------------------
    # FILTER + SEARCH COMBINATION
    # ---------------------------

    def test_filter_then_search(self):
        self.workspace.add_filter(FilterExpression.from_string("age > 30"))

        result = self.handlers["filter_graph"](self._apply(search="bob"))

        ids = {n.id for n in result.nodes}
        self.assertEqual(ids, {"2"})


if __name__ == "__main__":
    unittest.main()
