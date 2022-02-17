import copy
import datetime as dt
import json
import socket
import sys
import time
from collections import OrderedDict, defaultdict
from random import random
from uuid import uuid4

import eventlet
import jsonpickle
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import socketio
from dash import Dash, dash_table, dcc, html
from dash.dependencies import Input, Output, State

sio = socketio.Server()
app = socketio.WSGIApp(sio)

from typedefs_ob import Order, OrderBook, Trade, Trader


@sio.event
def connect(sid, environ):
    trader = Trader(bids=[], asks=[], trades=[], sid=sid, name=None)
    serv.order_book.traders.append(trader)
    serv.trader_lookup_dict[sid] = len(serv.order_book.traders) - 1
    print("connect ", sid)
    print(f"Traders: {[trader.sid for trader in serv.order_book.traders]}")


@sio.on("*")
def catch_all(event, sid, data):
    if event == "name":
        serv.order_book.traders[serv.trader_lookup_dict[sid]].name = data
    if event == "get_order_book":
        serv.handle_order_book_request(event, sid, data)
    if event in ["BID", "ASK"]:
        serv.handle_order(event, sid, data)
    pass


@sio.event
def disconnect(sid):
    print("disconnect ", sid)


class DashServer:
    def __init__(self) -> None:
        self.trader_lookup_dict = {}
        self.order_book = OrderBook(bids=[], asks=[], orders=[], trades=[], traders=[])
        print("init")

    def handle_order_book_request(self, event, sid, data):
        print("handling orderbook req")
        sio.emit("order_book", jsonpickle.encode(self.order_book), room=sid)

    def handle_order(self, event, sid, data):
        order = Order(
            o_type=event,
            sid=sid,
            price=int(data[0]),
            qty=int(data[1]),
            o_time=time.time(),
        )
        print("handling order")

        # check if this order is in cross
        resultant_trades = []
        if event == "BID":
            if self.order_book.asks:
                print(f"init matching bid qty {order.qty}")
                self.order_book.asks.sort(key=lambda x: (x.price, x.o_time))
                best_ask = self.order_book.asks[0]
                print(f"asks:{self.order_book.asks}")
                print(best_ask.price)
                print(order.price)
                print(type(order.price))
                while (order.price >= best_ask.price) and (order.qty > 0):
                    print(f"matching bid qty {order.qty}")
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
                        best_ask = self.order_book.asks[0]
                    elif order.qty < best_ask.qty:
                        # reduce resting order size
                        self.order_book.asks[0].qty = (
                            self.order_book.asks[0].qty - order.qty
                        )
                        order.qty = 0
                        # trade = {'bid':sid, 'ask': best_ask.sid, 'qty': order.qty, 'price': best_ask.price, 'time': order.time, 'resting_order': best_ask}
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
                print(f"init matching ask qty {order.qty}")
                self.order_book.bids.sort(key=lambda x: (-x.price, x.o_time))
                print(f"bids:{self.order_book.bids}")
                best_bid = self.order_book.bids[0]
                print(best_bid.price)
                print(order.price)
                print(type(order.price))
                while (order.price <= best_bid.price) and (order.qty > 0):
                    print(f"matching ask qty {order.qty}")
                    # trade occurs
                    if order.qty >= best_bid.qty:
                        # reduce agg order size
                        order.qty = order.qty - best_bid.qty
                        # trade = {'bid':best_bid.sid, 'ask': sid, 'qty': best_bid.qty, 'price': best_bid.price, 'time': order.time, 'resting_order': best_bid}
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
                        best_bid = self.order_book.bids[0]
                    elif order.qty < best_bid.qty:
                        # reduce resting order size
                        self.order_book.bids[0].qty = (
                            self.order_book.bids[0].qty - order.qty
                        )
                        order.qty = 0
                        # trade = {'bid':best_bid.sid, 'ask': sid, 'qty': order.qty, 'price': best_bid.price, 'time': order.time, 'resting_order': best_bid}
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
        # if not share it with clients and add to book
        if order.qty > 0:
            print(f"informing everyone of order: {jsonpickle.encode(order)}")
            self.order_book.orders.append(order)
            sio.emit("insert", jsonpickle.encode(order))
            if event == "BID":
                self.order_book.bids.append(order)
            elif event == "ASK":
                self.order_book.asks.append(order)
        for trade in resultant_trades:
            print(f"informing everyone of trade: {jsonpickle.encode(trade)}")
            sio.emit("trade", jsonpickle.encode(trade))
            self.order_book.trades.append(trade)
            self.order_book.traders[
                self.trader_lookup_dict[trade.bid_sid]
            ].trades.append(trade)
            self.order_book.traders[
                self.trader_lookup_dict[trade.ask_sid]
            ].trades.append(trade)
        print(self.order_book.trades)

        return 0

    def main(self, type=0):
        print("launching dash")
        es = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]
        dash_app = Dash(__name__, external_stylesheets=es)

        data_dict = OrderedDict(
            [
                ("Bids Qty", [0, 0, 0, 0, 1, 2, 4, 2]),
                ("Price", [i for i in range(200, 280, 10)]),
                ("Asks Qty", [1, 2, 4, 2, 0, 0, 0, 0]),
            ]
        )

        data = pd.DataFrame(data_dict)
        print(data.to_dict("records"))

        dash_app.layout = html.Div(
            children=[
                html.Div(
                    [
                        dcc.Interval(id="refresh_ui", interval=2000, n_intervals=0),
                        html.H1(id="labelUI", children=""),
                    ]
                ),
                html.H1(children="Mock Ledger SERVER", style={"textAlign": "center"}),
                dcc.Graph(id="graph"),
                html.Div(
                    [
                        dash_table.DataTable(
                            id="table",
                            style_data={
                                "width": "10px",
                                "maxWidth": "10px",
                                "minWidth": "10px",
                            },
                            columns=[{"name": i, "id": i} for i in data.columns],
                            data=data.to_dict("records"),
                            style_cell=dict(textAlign="left"),
                            style_header=dict(backgroundColor="paleturquoise"),
                        )
                    ],
                    style={"width": "50%", "align": "center", "flex": 1},
                ),
            ]
        )

        @dash_app.callback(
            Output("graph", "figure"), Input("refresh_ui", "n_intervals")
        )
        def display_color(mean=0):
            self.bid_px_q = []
            for order in self.order_book.bids:
                self.bid_px_q += [order.price] * int(order.qty)
            self.bid_px_q.sort(key=lambda x: float(x))
            self.ask_px_q = []
            for order in self.order_book.asks:
                self.ask_px_q += [order.price] * int(order.qty)
            self.ask_px_q.sort(key=lambda x: float(x))
            # data_bid = np.random.normal(200, 15, size=500)
            # data_ask = np.random.normal(100, 15, size=500)
            fig = go.Figure()
            tick_size = 1
            if self.order_book.bids and self.order_book.asks:
                bins = go.histogram.XBins(
                    end=self.ask_px_q[-1], size=tick_size, start=self.bid_px_q[0]
                )  # dict(start=0, end=475, size=15)
                fig.add_trace(go.Histogram(x=self.bid_px_q, xbins=bins))
                fig.add_trace(go.Histogram(x=self.ask_px_q, xbins=bins))
            else:
                fig.add_trace(go.Histogram(x=self.bid_px_q))
                fig.add_trace(go.Histogram(x=self.ask_px_q))
            # Overlay both histograms
            fig.update_layout(barmode="overlay")
            return fig

        @dash_app.callback(Output("table", "data"), Input("refresh_ui", "n_intervals"))
        def display_table(mean=0):
            print("trying to disp table")
            data_range = range(20, 26, 1)
            bids_dd = defaultdict(lambda x: 0)
            for row in data_range:
                bids_dd[row] = 0
            for order in self.order_book.bids:
                bids_dd[order.price] += order.qty
            asks_dd = defaultdict(lambda x: 0)
            for row in data_range:
                asks_dd[row] = 0
            for order in self.order_book.asks:
                asks_dd[order.price] += order.qty
            data_dict = OrderedDict(
                [
                    ("Bids Qty", list(bids_dd.values())[::-1]),
                    ("Price", list(data_range)[::-1]),
                    ("Asks Qty", list(asks_dd.values())[::-1]),
                ]
            )
            data = pd.DataFrame(data_dict)
            data = data.to_dict("records")
            print(data)
            # columns=[{"name": i, "id": i} for i in data.columns]
            return data

        @dash_app.callback(
            Output("labelUI", "children"), [Input("refresh_ui", "n_intervals")]
        )
        def update_interval(n):
            print(f"query:{n}")
            # sio.emit('BID', [200,3])
            return ""

        port = 6000 + round(1000 * random())
        dash_app.run_server(port=port, debug=True, use_reloader=False)
        print("running server")


if __name__ == "__main__":
    print(eventlet.spawn(eventlet.wsgi.server, eventlet.listen(("0.0.0.0", 5000)), app))
    print("starting dash")
    serv = DashServer()
    serv.main()
