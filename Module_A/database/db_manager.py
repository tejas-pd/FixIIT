from .table import Table


class DatabaseManager:
    """
    Simple database manager that manages multiple tables.
    """

    def __init__(self):
        self.tables = {}

    def create_table(self, table_name, primary_key="id"):
        """
        Create a new table.
        """
        if table_name in self.tables:
            raise ValueError("Table already exists")

        table = Table(table_name, primary_key)
        self.tables[table_name] = table

        return table

    def get_table(self, table_name):
        """
        Retrieve a table.
        """
        if table_name not in self.tables:
            raise ValueError("Table does not exist")

        return self.tables[table_name]

    def drop_table(self, table_name):
        """
        Delete a table.
        """
        if table_name in self.tables:
            del self.tables[table_name]

    def insert(self, table_name, record):
        """
        Insert record into table.
        """
        table = self.get_table(table_name)
        table.insert(record)

    def search(self, table_name, key):
        """
        Search record by key.
        """
        table = self.get_table(table_name)
        return table.search(key)

    def delete(self, table_name, key):
        """
        Delete record by key.
        """
        table = self.get_table(table_name)
        return table.delete(key)

    def update(self, table_name, key, new_record):
        """
        Update record.
        """
        table = self.get_table(table_name)
        return table.update(key, new_record)

    def range_query(self, table_name, start, end):
        """
        Range query on table.
        """
        table = self.get_table(table_name)
        return table.range_query(start, end)

    def show_tables(self):
        """
        List all tables.
        """
        return list(self.tables.keys())