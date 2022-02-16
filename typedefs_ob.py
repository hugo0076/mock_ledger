
from uuid import uuid4
import time

class Order:
    def __init__(self, o_type, sid, price, qty, o_time = time.time()):
        self.o_type = o_type
        self.sid = sid
        self.price = price
        self.qty = qty
        self.o_time = o_time
        self.id = uuid4().hex

class Trade:
    def __init__(self, bid, bid_sid, ask, ask_sid, price, qty, resting_order, resting_order_type, o_time = time.time()):
        self.bid = bid
        self.bid_sid = bid_sid
        self.ask = ask
        self.ask_sid = ask_sid
        self.price = price
        self.qty = qty
        self.o_time = o_time
        self.resting_order = resting_order
        self.resting_order_type = resting_order_type
        self.id = uuid4().hex

class Trader:
    def __init__(self, bids, asks, trades, sid, name):
        self.bids = bids
        self.asks = asks
        self.trades = trades
        self.id = uuid4().hex
        self.sid = sid
        self.name = name

class OrderBook:
    def __init__(self, bids, asks, orders, trades, traders):
        self.bids = bids
        self.asks = asks
        self.orders = orders
        self.trades = trades
        self.traders = traders