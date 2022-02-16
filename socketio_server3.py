import eventlet
import socketio
import datetime as dt
import json
from uuid import uuid4
import time
import sys
import copy
import jsonpickle
sio = socketio.Server()
app = socketio.WSGIApp(sio)

from typedefs_ob import Order, Trade, Trader, OrderBook, Settlement

trader_lookup_dict = {}
order_book = OrderBook(bids = [], asks = [], orders = [], trades = [], traders = [])

@sio.event
def connect(sid, environ):
    trader = Trader(bids=[], asks=[], trades=[], sid=sid, name=None)
    serv.order_book.traders.append(trader)
    serv.trader_lookup_dict[sid] = len(serv.order_book.traders) - 1
    print('connect ', sid)
    print(f'Traders: {[trader.sid for trader in serv.order_book.traders]}')


@sio.on('*')
def catch_all(event, sid, data):
    if event == 'name':
        serv.order_book.traders[serv.trader_lookup_dict[sid]].name = data
    if event == 'get_order_book':
        serv.handle_order_book_request(event, sid, data)
    if event == 'settle':
        serv.settle(event, sid, data)
    if event in ['BID', 'ASK']:
        serv.handle_order(event, sid, data)
    pass

@sio.event
def disconnect(sid):
    print('disconnect ', sid)

class MockServer():

    def __init__(self) -> None:
        self.trader_lookup_dict = {}
        self.order_book = OrderBook(bids = [], asks = [], orders = [], trades = [], traders = [])
        print('init')
    
    def settle(self, event, sid, data):
        print('Settling')
        settlement_price = float(data)
        for trader in self.order_book.traders:
            settlement = Settlement(trades=trader.trades, pnl = 0)
            cur_sid = trader.sid
            for trade in trader.trades:
                print(f'reconciling trade: {trade}')
                contract_val_bid = (settlement_price - trade.price)*trade.qty
                if trade.bid_sid == cur_sid:
                    settlement.pnl += contract_val_bid
                    descr = f'Bought {trade.qty} @ {trade.price} for a pnl of {contract_val_bid}, counterparty id = [{trade.ask_sid}]'
                    settlement.trades_text.append(descr)
                else:
                    settlement.pnl -= contract_val_bid
                    descr = f'Sold {trade.qty} @ {trade.price} for a pnl of {-contract_val_bid}, counterparty id = [{trade.bid_sid}]'
                    settlement.trades_text.append(descr)
            sio.emit('settlement', jsonpickle.encode(settlement), room=cur_sid)
        print('all settled')
        sys.exit(0)
    
    def handle_order_book_request(self, event, sid, data):
        print('handling orderbook req')
        sio.emit('order_book', jsonpickle.encode(self.order_book), room=sid)

    def handle_order(self,event, sid, data):
        order = Order(o_type=event, sid=sid, price=int(data[0]), qty=int(data[1]), o_time = time.time())
        print('handling order')

        # check if this order is in cross 
        resultant_trades = []
        if event == 'BID':
            if self.order_book.asks:
                print(f'init matching bid qty {order.qty}')
                self.order_book.asks.sort(key = lambda x: (x.price, x.o_time))
                best_ask = self.order_book.asks[0]
                print(f'asks:{self.order_book.asks}')
                print(best_ask.price)
                print(order.price)
                print(type(order.price))
                while (order.price >= best_ask.price) and (order.qty > 0):
                    print(f'matching bid qty {order.qty}')
                    #trade occurs
                    if order.qty >= best_ask.qty:
                        # reduce agg order size
                        order.qty = order.qty - best_ask.qty 
                        trade = Trade(bid = order.id, bid_sid = order.sid, ask = best_ask.id, ask_sid = best_ask.sid, price = best_ask.price, qty = best_ask.qty, resting_order = best_ask.id, resting_order_type = 'ASK', o_time = order.o_time)
                        resultant_trades.append(trade)
                        self.order_book.asks.pop(0)
                        if len(self.order_book.asks) > 0:
                            best_ask = self.order_book.asks[0]
                        else:
                            break
                    elif order.qty < best_ask.qty:
                        # reduce resting order size
                        self.order_book.asks[0].qty = self.order_book.asks[0].qty - order.qty
                        order.qty = 0
                        #trade = {'bid':sid, 'ask': best_ask.sid, 'qty': order.qty, 'price': best_ask.price, 'time': order.time, 'resting_order': best_ask}
                        trade = Trade(bid = order.id, bid_sid = order.sid, ask = best_ask.id, ask_sid = best_ask.sid, price = best_ask.price, qty = order.qty, resting_order = best_ask.id, resting_order_type = 'ASK', o_time = order.o_time)
                        resultant_trades.append(trade)
                        break
        elif event == 'ASK':
            if self.order_book.bids:
                print(f'init matching ask qty {order.qty}')
                self.order_book.bids.sort(key = lambda x: (-x.price, x.o_time))
                print(f'bids:{self.order_book.bids}')
                best_bid = self.order_book.bids[0]
                print(best_bid.price)
                print(order.price)
                print(type(order.price))
                while (order.price <= best_bid.price) and (order.qty > 0):
                    print(f'matching ask qty {order.qty}')
                    #trade occurs
                    if order.qty >= best_bid.qty:
                        # reduce agg order size
                        order.qty = order.qty - best_bid.qty 
                        #trade = {'bid':best_bid.sid, 'ask': sid, 'qty': best_bid.qty, 'price': best_bid.price, 'time': order.time, 'resting_order': best_bid}
                        trade = Trade(bid = best_bid.id, bid_sid = best_bid.sid, ask = order.id, ask_sid = order.sid, price = best_bid.price, qty = best_bid.qty, resting_order = best_bid.id, resting_order_type = 'BID', o_time = order.o_time)
                        resultant_trades.append(trade)
                        self.order_book.bids.pop(0)
                        if len(self.order_book.bids) > 0:
                            best_bid = self.order_book.bids[0]
                        else:
                            break
                    elif order.qty < best_bid.qty:
                        # reduce resting order size
                        self.order_book.bids[0].qty = self.order_book.bids[0].qty - order.qty
                        order.qty = 0
                        #trade = {'bid':best_bid.sid, 'ask': sid, 'qty': order.qty, 'price': best_bid.price, 'time': order.time, 'resting_order': best_bid}
                        trade = Trade(bid = best_bid.id, bid_sid = best_bid.sid, ask = order.id, ask_sid = order.sid, price = best_bid.price, qty = order.qty, resting_order = best_bid.id, resting_order_type = 'BID', o_time = order.o_time)
                        resultant_trades.append(trade)
                        break
        # if not share it with clients and add to book
        if order.qty > 0:
            print(f'informing everyone of order: {jsonpickle.encode(order)}')
            self.order_book.orders.append(order)
            sio.emit('insert', jsonpickle.encode(order))
            if event == 'BID':
                self.order_book.bids.append(order)
            elif event == 'ASK':
                self.order_book.asks.append(order)
        for trade in resultant_trades:
            print(f'informing everyone of trade: {jsonpickle.encode(trade)}')
            sio.emit('trade', jsonpickle.encode(trade))
            self.order_book.trades.append(trade)
            self.order_book.traders[self.trader_lookup_dict[trade.bid_sid]].trades.append(trade)
            self.order_book.traders[self.trader_lookup_dict[trade.ask_sid]].trades.append(trade)
        print(self.order_book.trades)
        return 0

if __name__ == '__main__':
    print('starting serv obj')
    serv = MockServer()
    eventlet.wsgi.server(eventlet.listen(('', 5001)), app)