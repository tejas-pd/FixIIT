from .bplustree import BPlusTree


class Table:
    """
    Table abstraction that stores records and uses
    a B+ Tree as an index on the primary key.
    """

    def __init__(self, name, primary_key="id", order=4):
        self.name = name
        self.primary_key = primary_key
        self.records = {}
        self.index = BPlusTree(order)

    def insert(self, record):
        """
        Insert a record into the table.
        Record must contain the primary key.
        """

        if self.primary_key not in record:
            raise ValueError("Primary key missing in record")

        key = record[self.primary_key]

        if key in self.records:
            raise ValueError("Duplicate primary key")

        self.records[key] = record
        self.index.insert(key, record)

    def search(self, key):
        """
        Search record using B+ Tree index.
        """
        return self.index.search(key)

    def update(self, key, new_record):
        """
        Update an existing record.
        """

        if key not in self.records:
            return False

        self.records[key] = new_record
        self.index.update(key, new_record)

        return True

    def delete(self, key):
        """
        Delete record from table.
        """

        if key not in self.records:
            return False

        del self.records[key]
        self.index.delete(key)

        return True

    def range_query(self, start_key, end_key):
        """
        Return records between two keys.
        """
        return self.index.range_query(start_key, end_key)

    def get_all(self):
        """
        Return all records.
        """
        return list(self.records.values())

    def visualize_index(self):
        """
        Visualize the B+ Tree index.
        """
        return self.index.visualize_tree()