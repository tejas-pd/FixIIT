import time
import random
import psutil
import os

from .bplustree import BPlusTree
from .bruteforce import BruteForceDB


class PerformanceAnalyzer:

    def __init__(self, size=20000):
        self.size = size
        self.keys = random.sample(range(1, size * 10), size)

    def memory_usage(self):
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024

    # INSERT TEST
    def test_insert(self):

        btree = BPlusTree()
        brute = BruteForceDB()

        start = time.perf_counter()
        for k in self.keys:
            btree.insert(k, k)
        btree_time = time.perf_counter() - start

        start = time.perf_counter()
        for k in self.keys:
            brute.insert(k, k)
        brute_time = time.perf_counter() - start

        return btree_time, brute_time

    # SEARCH TEST
    def test_search(self):

        btree = BPlusTree()
        brute = BruteForceDB()

        for k in self.keys:
            btree.insert(k, k)
            brute.insert(k, k)

        search_keys = random.sample(self.keys, 100)

        start = time.perf_counter()
        for _ in range(1000):
            for k in search_keys:
                btree.search(k)
        btree_time = time.perf_counter() - start

        start = time.perf_counter()
        for _ in range(1000):
            for k in search_keys:
                brute.search(k)
        brute_time = time.perf_counter() - start

        return btree_time, brute_time

    # DELETE TEST
    def test_delete(self):

        btree = BPlusTree()
        brute = BruteForceDB()

        for k in self.keys:
            btree.insert(k, k)
            brute.insert(k, k)

        delete_keys = random.sample(self.keys, 100)

        start = time.perf_counter()
        for _ in range(500):
            for k in delete_keys:
                btree.delete(k)
        btree_time = time.perf_counter() - start

        start = time.perf_counter()
        for _ in range(500):
            for k in delete_keys:
                brute.delete(k)
        brute_time = time.perf_counter() - start

        return btree_time, brute_time

    # RANGE QUERY TEST
    def test_range_query(self):

        btree = BPlusTree()
        brute = BruteForceDB()

        for k in self.keys:
            btree.insert(k, k)
            brute.insert(k, k)

        start_key = random.choice(self.keys[:len(self.keys)//2])
        end_key = random.choice(self.keys[len(self.keys)//2:])

        start = time.perf_counter()
        for _ in range(500):
            btree.range_query(start_key, end_key)
        btree_time = time.perf_counter() - start

        start = time.perf_counter()
        for _ in range(500):
            brute.range_query(start_key, end_key)
        brute_time = time.perf_counter() - start

        return btree_time, brute_time