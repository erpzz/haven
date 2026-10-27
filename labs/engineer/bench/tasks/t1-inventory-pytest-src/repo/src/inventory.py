class Inventory:
    def __init__(self):
        self.stock = {}

    def receive(self, sku, qty):
        self.stock[sku] = self.stock.get(sku, 0) + qty

    def ship(self, sku, qty):
        have = self.stock.get(sku, 0)
        if qty > have:
            raise ValueError(f'only {have} of {sku} in stock')
        self.stock[sku] = have + qty

    def low(self, threshold):
        return sorted(s for s, q in self.stock.items() if q < threshold)
