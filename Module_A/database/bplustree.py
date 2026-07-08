import math

from graphviz import Digraph


class BPlusTreeNode:
    def __init__(self, leaf=False):
        self.leaf = leaf
        self.keys = []
        self.values = []
        self.children = []
        self.next = None


class BPlusTree:
    def __init__(self, order=4):
        self.root = BPlusTreeNode(True)
        self.order = order

    def _min_leaf_keys(self):
        return max(1, math.ceil((self.order - 1) / 2))

    def _min_internal_children(self):
        return max(2, math.ceil(self.order / 2))

    def _first_key(self, node):
        current = node

        while current and not current.leaf:
            current = current.children[0]

        if current and current.keys:
            return current.keys[0]

        return None

    def _refresh_internal_keys(self, node):
        if node.leaf:
            return

        node.keys = [
            first_key
            for first_key in (self._first_key(child) for child in node.children[1:])
            if first_key is not None
        ]

    def search(self, key):
        node = self.root

        while not node.leaf:
            i = 0
            while i < len(node.keys) and key >= node.keys[i]:
                i += 1
            node = node.children[i]

        for i, k in enumerate(node.keys):
            if k == key:
                return node.values[i]

        return None

    def insert(self, key, value):
        root = self.root

        if len(root.keys) == self.order - 1:
            new_root = BPlusTreeNode()
            new_root.children.append(self.root)
            self._split_child(new_root, 0)
            self.root = new_root

        self._insert_non_full(self.root, key, value)

    def _insert_non_full(self, node, key, value):

        if node.leaf:
            i = 0
            while i < len(node.keys) and key > node.keys[i]:
                i += 1

            node.keys.insert(i, key)
            node.values.insert(i, value)

        else:
            i = 0
            while i < len(node.keys) and key >= node.keys[i]:
                i += 1

            child = node.children[i]

            if len(child.keys) == self.order - 1:
                self._split_child(node, i)

                if key >= node.keys[i]:
                    i += 1

            self._insert_non_full(node.children[i], key, value)

    def _split_child(self, parent, index):

        node = parent.children[index]
        mid = len(node.keys) // 2

        new_node = BPlusTreeNode(node.leaf)

        if node.leaf:
            new_node.keys = node.keys[mid:]
            new_node.values = node.values[mid:]

            node.keys = node.keys[:mid]
            node.values = node.values[:mid]

            new_node.next = node.next
            node.next = new_node

            parent.keys.insert(index, new_node.keys[0])

        else:
            parent.keys.insert(index, node.keys[mid])

            new_node.keys = node.keys[mid + 1:]
            new_node.children = node.children[mid + 1:]

            node.keys = node.keys[:mid]
            node.children = node.children[:mid + 1]

        parent.children.insert(index + 1, new_node)

    def delete(self, key):
        deleted = self._delete(self.root, key)

        if not deleted:
            return False

        if not self.root.leaf and len(self.root.children) == 1:
            self.root = self.root.children[0]

        self._refresh_internal_keys(self.root)
        return True

    def _delete(self, node, key):
        if node.leaf:
            if key not in node.keys:
                return False

            index = node.keys.index(key)
            node.keys.pop(index)
            node.values.pop(index)
            return True

        i = 0
        while i < len(node.keys) and key >= node.keys[i]:
            i += 1

        child = node.children[i]
        deleted = self._delete(child, key)

        if not deleted:
            return False

        self._fix_child_underflow(node, i)
        self._refresh_internal_keys(node)
        return True

    def _fix_child_underflow(self, parent, index):
        if index >= len(parent.children):
            return

        child = parent.children[index]

        if child.leaf:
            min_keys = self._min_leaf_keys()

            if len(child.keys) >= min_keys:
                return

            if index > 0:
                left = parent.children[index - 1]
                if len(left.keys) > min_keys:
                    child.keys.insert(0, left.keys.pop())
                    child.values.insert(0, left.values.pop())
                    self._refresh_internal_keys(parent)
                    return

            if index + 1 < len(parent.children):
                right = parent.children[index + 1]
                if len(right.keys) > min_keys:
                    child.keys.append(right.keys.pop(0))
                    child.values.append(right.values.pop(0))
                    self._refresh_internal_keys(parent)
                    return

            if index > 0:
                left = parent.children[index - 1]
                left.keys.extend(child.keys)
                left.values.extend(child.values)
                left.next = child.next
                parent.children.pop(index)
            elif index + 1 < len(parent.children):
                right = parent.children[index + 1]
                child.keys.extend(right.keys)
                child.values.extend(right.values)
                child.next = right.next
                parent.children.pop(index + 1)

            self._refresh_internal_keys(parent)
            return

        min_children = self._min_internal_children()

        if len(child.children) >= min_children:
            return

        if index > 0:
            left = parent.children[index - 1]
            if len(left.children) > min_children:
                child.children.insert(0, left.children.pop())
                self._refresh_internal_keys(left)
                self._refresh_internal_keys(child)
                self._refresh_internal_keys(parent)
                return

        if index + 1 < len(parent.children):
            right = parent.children[index + 1]
            if len(right.children) > min_children:
                child.children.append(right.children.pop(0))
                self._refresh_internal_keys(right)
                self._refresh_internal_keys(child)
                self._refresh_internal_keys(parent)
                return

        if index > 0:
            left = parent.children[index - 1]
            left.children.extend(child.children)
            self._refresh_internal_keys(left)
            parent.children.pop(index)
        elif index + 1 < len(parent.children):
            right = parent.children[index + 1]
            child.children.extend(right.children)
            self._refresh_internal_keys(child)
            parent.children.pop(index + 1)

        self._refresh_internal_keys(parent)

    def update(self, key, new_value):

        node = self.root

        while not node.leaf:
            i = 0
            while i < len(node.keys) and key >= node.keys[i]:
                i += 1
            node = node.children[i]

        for i, k in enumerate(node.keys):
            if k == key:
                node.values[i] = new_value
                return True

        return False

    def range_query(self, start_key, end_key):

        node = self.root

        while not node.leaf:
            i = 0
            while i < len(node.keys) and start_key >= node.keys[i]:
                i += 1
            node = node.children[i]

        result = []

        while node:
            for k, v in zip(node.keys, node.values):
                if start_key <= k <= end_key:
                    result.append((k, v))
                elif k > end_key:
                    return result

            node = node.next

        return result

    def get_all(self):

        node = self.root

        while not node.leaf:
            node = node.children[0]

        result = []

        while node:
            for k, v in zip(node.keys, node.values):
                result.append((k, v))
            node = node.next

        return result

    def visualize_tree(self):

        dot = Digraph()
        dot.attr(rankdir="TB")

        self._add_nodes(dot, self.root)
        self._add_edges(dot, self.root)

        return dot

    def _add_nodes(self, dot, node):

        node_id = str(id(node))
        label = "|".join(str(k) for k in node.keys)
        shape = "record"

        dot.node(node_id, label, shape=shape)

        if not node.leaf:
            for child in node.children:
                self._add_nodes(dot, child)

    def _add_edges(self, dot, node):

        if not node.leaf:
            for child in node.children:
                dot.edge(str(id(node)), str(id(child)))
                self._add_edges(dot, child)

        if node.leaf and node.next:
            dot.edge(str(id(node)), str(id(node.next)), style="dashed")
