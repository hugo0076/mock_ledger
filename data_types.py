import datetime as dt

class Player:
    def __init__(self, name: str):
        self.name = name
        self.trades = []
        self.pnl = 0


class Order:
    def __init__(self, side: bool, player: Player, size: int, price: float, timestamp=dt.date.today()):
        self.side = side
        self.player = player
        self.size = size
        self.price = price
        self.timestamp = timestamp


class Trade:
    def __init__(self, resting_order: Order, aggressive_order: Order, size: int, price: float):
        self.restingOrder = resting_order
        self.aggressiveOrder = aggressive_order
        self.size = size
        self.price = price
        self.timestamp = aggressive_order.timestamp


class OrderBook:
    def __init__(self):
        self.buy_orders = []
        self.sell_orders = []
        self.bestPrice = None


class Market:
    def __init__(self, trades: list[Trade], order_book: OrderBook):
        self.currentPrice = None
        self.settlementPrice = None
        self.price = None
        self.trades = trades
        self.order_book = order_book