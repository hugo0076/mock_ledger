#import socketio
#
#sio = socketio.AsyncServer()
#
#@sio.on('*')
#async def catch_all(event, sid, data):
#    print(f'event {event} happened, sid {sid}, data {data}')
#    pass
#
#@sio.event
#def connect(sid, environ, auth):
#    print('server connect ', sid)
#
#@sio.event
#def disconnect(sid):
#    print('server disconnect ', sid)
#
#
##sio.emit('my event', {'data': 'foobar'})

# set async_mode to 'threading', 'eventlet', 'gevent' or 'gevent_uwsgi' to
# force a mode else, the best mode is selected automatically from what's
# installed
import eventlet
import socketio
import datetime as dt
import json
from uuid import uuid4
import time
sio = socketio.Server()
app = socketio.WSGIApp(sio)

class Order:
    def __init__(self, o_type, sid, price, qty, o_time = time.time()):
        self.o_type = o_type
        self.sid = sid
        self.price = price
        self.qty = qty
        self.o_time = o_time
        self.id = uuid4().hex

#trade = {'bid':sid, 'ask': best_ask.sid, 'qty': best_ask.qty, 'price': best_ask.price, 'time': order.time, 'resting_order': best_ask}
class Trade:
    def __init__(self, bid, ask, price, qty, resting_order, resting_order_type, o_time = time.time()):
        self.bid = bid
        self.ask = ask
        self.price = price
        self.qty = qty
        self.o_time = o_time
        self.resting_order = resting_order
        self.resting_order_type = resting_order_type
        self.id = uuid4().hex

@sio.event
def connect(sid, environ):
    print('connect ', sid)

@sio.on('*')
def catch_all(event, sid, data):
    if event in ['BID', 'ASK']:
        handle_order(event, sid, data)
    pass

@sio.event
def disconnect(sid):
    print('disconnect ', sid)

bids = []
asks = []
order_book = []
trades = []

def handle_order(event, sid, data):
    order = Order(o_type=event, sid=sid, price=int(data[0]), qty=int(data[1]), o_time = time.time())
    print('handling order')
    
    # check if this order is in cross 
    resultant_trades = []
    if event == 'BID':
        if asks:
            print(f'init matching bid qty {order.qty}')
            asks.sort(key = lambda x: (x.price, x.o_time))
            best_ask = asks[0]
            print(f'asks:{asks}')
            print(best_ask.price)
            print(order.price)
            print(type(order.price))
            while (order.price >= best_ask.price) and (order.qty > 0):
                print(f'matching bid qty {order.qty}')
                #trade occurs
                if order.qty >= best_ask.qty:
                    # reduce agg order size
                    order.qty = order.qty - best_ask.qty 
                    trade = Trade(bid = order.id, ask = best_ask.id, price = best_ask.price, qty = best_ask.qty, resting_order = best_ask.id, resting_order_type = 'ASK', o_time = order.o_time)
                    resultant_trades.append(trade)
                    asks.pop(0)
                    best_ask = asks[0]
                elif order.qty < best_ask.qty:
                    # reduce resting order size
                    asks[0].qty = asks[0].qty - order.qty
                    order.qty = 0
                    #trade = {'bid':sid, 'ask': best_ask.sid, 'qty': order.qty, 'price': best_ask.price, 'time': order.time, 'resting_order': best_ask}
                    trade = Trade(bid = order.id, ask = best_ask.id, price = best_ask.price, qty = order.qty, resting_order = best_ask.id, resting_order_type = 'ASK', o_time = order.o_time)
                    resultant_trades.append(trade)
                    break
    elif event == 'ASK':
        if bids:
            print(f'init matching ask qty {order.qty}')
            bids.sort(key = lambda x: (-x.price, x.o_time))
            print(f'bids:{bids}')
            best_bid = bids[0]
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
                    trade = Trade(bid = best_bid.id, ask = order.id, price = best_bid.price, qty = best_bid.qty, resting_order = best_bid.id, resting_order_type = 'BID', o_time = order.o_time)
                    resultant_trades.append(trade)
                    bids.pop(0)
                    best_bid = bids[0]
                elif order.qty < best_bid.qty:
                    # reduce resting order size
                    bids[0].qty = bids[0].qty - order.qty
                    order.qty = 0
                    #trade = {'bid':best_bid.sid, 'ask': sid, 'qty': order.qty, 'price': best_bid.price, 'time': order.time, 'resting_order': best_bid}
                    trade = Trade(bid = best_bid.id, ask = order.id, price = best_bid.price, qty = order.qty, resting_order = best_bid.id, resting_order_type = 'BID', o_time = order.o_time)
                    resultant_trades.append(trade)
                    break
    # if not share it with clients and add to book
    if order.qty > 0:
        print(f'informing everyone of order: {order}')
        order_book.append(order)
        sio.emit('insert', json.dumps(order.__dict__))
        if event == 'BID':
            bids.append(order)
        elif event == 'ASK':
            asks.append(order)
    for trade in resultant_trades:
        print(f'informing everyone of trade: {trade}')
        sio.emit('trade', json.dumps(trade.__dict__))
        trades.append(trade)
    print(trades)
    
    return 0

if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('', 5000)), app)