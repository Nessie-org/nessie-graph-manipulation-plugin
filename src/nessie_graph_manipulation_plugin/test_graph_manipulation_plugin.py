import unittest

from nessie_api.models import (
    Graph,
    Node,
    Attribute,
    Workspace,
    Action,
    GraphType,
)

from graph_manipulation_plugin import graph_manipulation_plugin


class TestGraphManipulationPlugin(unittest.TestCase):

    def setUp(self):
        self.graph = Graph(GraphType.DIRECTED)

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

    # ---------------------------
    # BASIC FUNCTIONALITY
    # ---------------------------

    def test_filter_basic(self):
        action = Action("filter", {
            "workspace": self.workspace,
            "filter": "age > 30"
        })

        result = self.handlers["filter"](action)

        ids = {n.id for n in result.nodes}
        self.assertEqual(ids, {"2", "3"})

    def test_search_basic(self):
        action = Action("search", {
            "workspace": self.workspace,
            "query": "bob"
        })

        result = self.handlers["search"](action)

        ids = {n.id for n in result.nodes}
        self.assertEqual(ids, {"2"})

    # ---------------------------
    # FILTER EDGE CASES
    # ---------------------------

    def test_filter_no_results(self):
        action = Action("filter", {
            "workspace": self.workspace,
            "filter": "age > 100"
        })

        result = self.handlers["filter"](action)
        self.assertEqual(len(result.nodes), 0)

    def test_filter_missing_attribute(self):
        action = Action("filter", {
            "workspace": self.workspace,
            "filter": "salary > 1000"
        })

        result = self.handlers["filter"](action)
        self.assertEqual(len(result.nodes), 0)

    def test_filter_type_mismatch(self):
        action = Action("filter", {
            "workspace": self.workspace,
            "filter": 'age == "Alice"'
        })

        with self.assertRaises(TypeError):
            self.handlers["filter"](action)

    def test_multiple_filters(self):
        self.handlers["filter"](Action("filter", {
            "workspace": self.workspace,
            "filter": "age > 20"
        }))

        result = self.handlers["filter"](Action("filter", {
            "workspace": self.workspace,
            "filter": "age < 40"
        }))

        ids = {n.id for n in result.nodes}
        self.assertEqual(ids, {"1", "2"})

    # ---------------------------
    # SEARCH EDGE CASES
    # ---------------------------

    def test_search_case_insensitive(self):
        action = Action("search", {
            "workspace": self.workspace,
            "query": "ALICE"
        })

        result = self.handlers["search"](action)

        ids = {n.id for n in result.nodes}
        self.assertEqual(ids, {"1"})

    def test_search_empty_query(self):
        action = Action("search", {
            "workspace": self.workspace,
            "query": ""
        })

        result = self.handlers["search"](action)

        self.assertEqual(len(result.nodes), 3)

    def test_search_no_match(self):
        action = Action("search", {
            "workspace": self.workspace,
            "query": "zzz"
        })

        result = self.handlers["search"](action)

        self.assertEqual(len(result.nodes), 0)

    # ---------------------------
    # UNDO / REDO
    # ---------------------------

    def test_undo(self):
        self.handlers["filter"](Action("filter", {
            "workspace": self.workspace,
            "filter": "age > 30"
        }))

        result = self.handlers["undo"](Action("undo", {
            "workspace": self.workspace
        }))

        ids = {n.id for n in result.nodes}
        self.assertEqual(ids, {"1", "2", "3"})

    def test_redo(self):
        self.handlers["filter"](Action("filter", {
            "workspace": self.workspace,
            "filter": "age > 30"
        }))

        self.handlers["undo"](Action("undo", {
            "workspace": self.workspace
        }))

        result = self.handlers["redo"](Action("redo", {
            "workspace": self.workspace
        }))

        ids = {n.id for n in result.nodes}
        self.assertEqual(ids, {"2", "3"})

    def test_undo_without_history(self):
        result = self.handlers["undo"](Action("undo", {
            "workspace": self.workspace
        }))

        self.assertEqual(len(result.nodes), 3)

    # ---------------------------
    # RESET
    # ---------------------------

    def test_reset(self):
        self.handlers["filter"](Action("filter", {
            "workspace": self.workspace,
            "filter": "age > 30"
        }))

        result = self.handlers["reset"](Action("reset", {
            "workspace": self.workspace
        }))

        ids = {n.id for n in result.nodes}
        self.assertEqual(ids, {"1", "2", "3"})

    # ---------------------------
    # FILTER + SEARCH COMBINATION
    # ---------------------------

    def test_filter_then_search(self):
        self.handlers["filter"](Action("filter", {
            "workspace": self.workspace,
            "filter": "age > 30"
        }))

        result = self.handlers["search"](Action("search", {
            "workspace": self.workspace,
            "query": "bob"
        }))

        ids = {n.id for n in result.nodes}
        self.assertEqual(ids, {"2"})

    # ---------------------------
    # INVALID PAYLOADS
    # ---------------------------

    def test_invalid_filter_type(self):
        action = Action("filter", {
            "workspace": self.workspace,
            "filter": 123
        })

        with self.assertRaises(TypeError):
            self.handlers["filter"](action)


if __name__ == "__main__":
    unittest.main()
