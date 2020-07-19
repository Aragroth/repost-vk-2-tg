import bisect
import pickle
import os.path
import random


class Store:
    """
    Storage with binary search/adding, that
    saves itself after each change action
    """

    def __init__(self, name):
        self.name = name
        self._store = []

        if not os.path.isfile(f'assets/{self.name}.bin'):
            self.save_store(clear=True)

        self.load_store()

    def save_store(self, clear=False):
        """ clear=True is also equal to create_store """

        with open(f'assets/{self.name}.bin', 'wb') as fp:
            pickle.dump([] if clear else self._store, fp)

    def load_store(self):
        with open(f'assets/{self.name}.bin', 'rb') as fp:
            self._store = pickle.load(fp)

    def assign_list(self, data: list):
        self._store = list(data)
        self.save_store()

    def append(self, number):
        if not self.contains(number):
            bisect.insort(self._store, number)
        self.save_store()

    def clear(self):
        self._store = []
        self.save_store(clear=True)

    def contains(self, elem):
        self.load_store()

        index = bisect.bisect_left(self._store, elem)
        if index < len(self._store):
            return self._store[index] == elem
        return False

    def pop_random(self):
        random_item_ind = random.randint(0, len(self._store) - 1)
        random_item = self._store[random_item_ind]
        del self._store[random_item_ind]
        self.save_store()

        return random_item

    def __len__(self):
        return len(self._store)

    def __getitem__(self, key):
        return self._store[key]

    def __repr__(self):
        return str(self._store)
