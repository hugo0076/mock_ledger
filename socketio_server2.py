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
sio = socketio.Server()
app = socketio.WSGIApp(sio)

@sio.event
def connect(sid, environ):
    print('connect ', sid)

@sio.on('*')
def catch_all(event, sid, data):
    print(f'caught {event} and {data} from {sid}')
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
    order = {'type' : event, 'sid': sid, 'price': data[0], 'qty': data[1], 'time': dt.now()}
    print('handling order')
    
    # check if this order is in cross 
    if event == 'BID' and asks:
        asks.sort(key = lambda x: (x['price'], x['time']))
        best_ask = asks.pop(0)
        while order['price'] >= best_ask['price'] and order['qty'] > 0:
            print(f'matching qty {order["qty"]}')
            #trade occurs
            if order['qty'] > best_ask['qty']:
                # reduce agg order size
                order['qty'] = order['qty'] - best_ask['qty'] 
                trade = {'bid':sid, 'ask': best_ask['sid'], 'qty': best_ask['qty'], 'price': best_ask['price'], 'time': order['time']}
                trades.append(trade)
            elif order['qty'] < best_ask['qty']:
                # reduce resting order size
                best_ask['qty'] = best_ask['qty'] - order['qty'] 
                trade = {'bid':sid, 'ask': best_ask['sid'], 'qty': order['qty'], 'price': best_ask['price'], 'time': order['time']}
                trades.append(trade)
            elif order['qty'] == best_ask['qty']:
                # remove both
                trade = {'bid':sid, 'ask': best_ask['sid'], 'qty': order['qty'], 'price': best_ask['price'], 'time': order['time']}
                trades.append(trade)
            qty = min(order['qty'], best_ask['qty'])
            trade = 
            trades.append()
    elif event == 'ASK' and bids:
        sorted_bids = sorted(bids, key = lambda x: (x['price'], x['time']))
    # if not share it with clients and add to book
    order_book.append(order)
    if event == 'BID':
        bids.append(order)
    elif event == 'ASK':
        asks.append(order)
    print(order_book)
    print('sending out data')
    sio.emit('update', order)
    return 0

if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('', 5000)), app)