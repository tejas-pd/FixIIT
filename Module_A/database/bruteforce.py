class BruteForceDB:
    """
    Simple database using a Python list.
    Used as a baseline for performance comparison.
    """

    def __init__(self):
        self.data = []

    def insert(self, key, value=None):
        """
        Insert a key-value pair.
        """
        self.data.append((key, value))

    def search(self, key):
        """
        Search for a key using linear search.
        """
        for k, v in self.data:
            if k == key:
                return v
        return None

    def delete(self, key):
        """
        Delete a key from the database.
        """
        for i, (k, v) in enumerate(self.data):
            if k == key:
                del self.data[i]
                return True
        return False

    def range_query(self, start, end):
        """
        Return all key-value pairs within range.
        """
        result = []
        for k, v in self.data:
            if start <= k <= end:
                result.append((k, v))
        return result

    def get_all(self):
        """
        Return all stored records.
        """
        return self.data