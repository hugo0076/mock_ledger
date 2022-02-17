import sys
import time
from uuid import uuid4
from typedefs_ob import Order, OrderBook, Settlement, Trade, Trader
import eventlet
import jsonpickle
import socketio

class MockServer:
    def __init__(self, order_book) -> None:
        self.trader_lookup_dict = {}
        self.order_book = order_book

    def settle(self, data):
        print("Settling")
        settlement_price = float(data)
        for trader in self.order_book.traders:
            settlement = Settlement(trades=trader.trades, pnl=0)
            cur_sid = trader.sid
            for trade in trader.trades:
                print(f"reconciling trade: {trade}")
                contract_val_bid = (settlement_price - trade.price) * trade.qty
                if trade.bid_sid == trade.ask_sid:
                    descr = f"Wash Traded {trade.qty} @ {trade.price} compliance will see you tomorrow, counterparty id = [you lol]"
                    settlement.trades_text.append(descr)
                elif trade.bid_sid == cur_sid:
                    settlement.pnl += contract_val_bid
                    descr = f"Bought {trade.qty} @ {trade.price} for a pnl of {contract_val_bid}, counterparty id = [{trade.ask_sid}]"
                    settlement.trades_text.append(descr)
                else:
                    settlement.pnl -= contract_val_bid
                    descr = f"Sold {trade.qty} @ {trade.price} for a pnl of {-contract_val_bid}, counterparty id = [{trade.bid_sid}]"
                    settlement.trades_text.append(descr)
            sio.emit("settlement", jsonpickle.encode(settlement), room=cur_sid)
        print("Settlement finished")
        sys.exit(0)

    def handle_order_book_request(self, sid):
        sio.emit("order_book", jsonpickle.encode(self.order_book), room=sid)

    def handle_cancel(self, data):
        for order in self.order_book.bids:
            if order.price == float(data):
                sio.emit("cancel", jsonpickle.encode(order))
        for order in self.order_book.asks:
            if order.price == float(data):
                sio.emit("cancel", jsonpickle.encode(order))

        self.order_book.bids = [
            item for item in self.order_book.bids if not item.price == float(data)
        ]
        self.order_book.asks = [
            item for item in self.order_book.asks if not item.price == float(data)
        ]

    def handle_order(self, event, sid, data):
        order = Order(
            o_type=event, sid=sid, price=data[0], qty=int(data[1]), o_time=time.time()
        )
        # check if this order is in cross
        resultant_trades = []
        if event == "BID":
            if self.order_book.asks:
                self.order_book.asks.sort(key=lambda x: (x.price, x.o_time))
                best_ask = self.order_book.asks[0]
                while (order.price >= best_ask.price) and (order.qty > 0):
                    # trade occurs
                    if order.qty >= best_ask.qty:
                        # reduce agg order size
                        order.qty = order.qty - best_ask.qty
                        trade = Trade(
                            bid=order.id,
                            bid_sid=order.sid,
                            ask=best_ask.id,
                            ask_sid=best_ask.sid,
                            price=best_ask.price,
                            qty=best_ask.qty,
                            resting_order=best_ask.id,
                            resting_order_type="ASK",
                            o_time=order.o_time,
                        )
                        resultant_trades.append(trade)
                        self.order_book.asks.pop(0)
                        if len(self.order_book.asks) > 0:
                            best_ask = self.order_book.asks[0]
                        else:
                            break
                    elif order.qty < best_ask.qty:
                        # reduce resting order size
                        self.order_book.asks[0].qty = (
                            self.order_book.asks[0].qty - order.qty
                        )
                        order.qty = 0
                        trade = Trade(
                            bid=order.id,
                            bid_sid=order.sid,
                            ask=best_ask.id,
                            ask_sid=best_ask.sid,
                            price=best_ask.price,
                            qty=order.qty,
                            resting_order=best_ask.id,
                            resting_order_type="ASK",
                            o_time=order.o_time,
                        )
                        resultant_trades.append(trade)
                        break
        elif event == "ASK":
            if self.order_book.bids:
                self.order_book.bids.sort(key=lambda x: (-x.price, x.o_time))
                best_bid = self.order_book.bids[0]
                while (order.price <= best_bid.price) and (order.qty > 0):
                    # trade occurs
                    if order.qty >= best_bid.qty:
                        # reduce agg order size
                        order.qty = order.qty - best_bid.qty
                        trade = Trade(
                            bid=best_bid.id,
                            bid_sid=best_bid.sid,
                            ask=order.id,
                            ask_sid=order.sid,
                            price=best_bid.price,
                            qty=best_bid.qty,
                            resting_order=best_bid.id,
                            resting_order_type="BID",
                            o_time=order.o_time,
                        )
                        resultant_trades.append(trade)
                        self.order_book.bids.pop(0)
                        if len(self.order_book.bids) > 0:
                            best_bid = self.order_book.bids[0]
                        else:
                            break
                    elif order.qty < best_bid.qty:
                        # reduce resting order size
                        self.order_book.bids[0].qty = (
                            self.order_book.bids[0].qty - order.qty
                        )
                        order.qty = 0
                        trade = Trade(
                            bid=best_bid.id,
                            bid_sid=best_bid.sid,
                            ask=order.id,
                            ask_sid=order.sid,
                            price=best_bid.price,
                            qty=order.qty,
                            resting_order=best_bid.id,
                            resting_order_type="BID",
                            o_time=order.o_time,
                        )
                        resultant_trades.append(trade)
                        break
        # if not, or theres is remaining unmatched size: share it with clients and add to book
        if order.qty > 0:
            print(f"informing everyone of order: {jsonpickle.encode(order)}")
            self.order_book.orders.append(order)
            sio.emit("insert", jsonpickle.encode(order))
            if event == "BID":
                self.order_book.bids.append(order)
            elif event == "ASK":
                self.order_book.asks.append(order)
        # if any trades occur, reconcile them
        for trade in resultant_trades:
            print(f"informing everyone of trade: {jsonpickle.encode(trade)}")
            sio.emit("trade", jsonpickle.encode(trade))
            self.order_book.trades.append(trade)
            self.order_book.traders[
                self.trader_lookup_dict[trade.bid_sid]
            ].trades.append(trade)
            if not trade.bid_sid == trade.ask_sid:
                self.order_book.traders[
                    self.trader_lookup_dict[trade.ask_sid]
                ].trades.append(trade)
        return 0


if __name__ == "__main__":
    if len(sys.argv[1:]) == 1:
        tick_size = float(sys.argv[1])
    else:
        print('Please specify tick size')
        sys.exit(0)
    sio = socketio.Server()
    app = socketio.WSGIApp(sio)
    order_book = OrderBook(
        bids=[], asks=[], orders=[], trades=[], traders=[], tick_size=tick_size
    )
    print("starting serv obj")
    serv = MockServer(order_book)
    eventlet.wsgi.server(eventlet.listen(("", 5001)), app)

@sio.event
def connect(sid, environ):
    trader = Trader(bids=[], asks=[], trades=[], sid=sid, name=None)
    serv.order_book.traders.append(trader)
    serv.trader_lookup_dict[sid] = len(serv.order_book.traders) - 1
    print("connected", sid)
    print(f"Traders: {[trader.sid for trader in serv.order_book.traders]}")


@sio.on("*")
def catch_all(event, sid, data):
    if event == "name":
        serv.order_book.traders[serv.trader_lookup_dict[sid]].name = data
    if event == "get_order_book":
        serv.handle_order_book_request(sid)
    if event == "cancel":
        serv.handle_cancel(data)
    if event == "get_sid":
        print("sending sid")
        sio.emit("sid", str(sid), room=sid)
    if event == "settle":
        serv.settle(data)
    if event in ["BID", "ASK"]:
        serv.handle_order(event, sid, data)
    pass

@sio.event
def disconnect(sid):
    serv.order_book.traders.pop(serv.trader_lookup_dict[sid])
    print("disconnected", sid)






