#!/usr/bin/env python3
import threading
import os
import sys
import time
import string
import re
from pathlib import Path
from functools import partial, partialmethod

from sanic import Sanic
from sanic.response import json, html
from sanic import response
from sanic.response import file

import dataclasses
from dataclasses import dataclass
from typing import Optional, Dict, List
import json

import socket
import concurrent
import websockets
import logging
from datetime import datetime, timedelta


import asyncio

import re


# config
HOST = "0.0.0.0"
PORT = 8000

SCOREBOARD_JSONPATH = "/data/"
SCOREBOARD_JSON = SCOREBOARD_JSONPATH + "scoreboard.json"
JSON_UPDATE_INTERVAL = 180  # [s], given by engine, to warn on input delay only
# 0 for filenames, 1 for SCOREBOARD_JSON.data
LASTROUNDINDICATOR = 1

scoregex = re.compile("scoreboard([0-9]+).json")

app = Sanic(__name__)
app.config['REQUEST_TIMEOUT'] = 30
app.config['KEEP_ALIVE'] = True
app.config['KEEP_ALIVE_TIMEOUT'] = 30
app.config['GRACEFUL_SHUTDOWN_TIMEOUT'] = 5

# TODO der accesslog koennte vom format her noch angeglichen werden. sanic nutzt auch falsche zeit, offset fehlt
SANIC_ACCESSLOG = True
SANIC_DEBUG = False

logging.PERF = 5                       # define custom log level
# LOGLEVEL must be <= LOGLEVELCONSOLE, otherwise LOGLEVELCONSOLE will be behave being on height of LOGLEVEL
LOGLEVEL = logging.NOTSET
# possible values: 0=NOTSET < 5=PERF < 10=DEBUG < 20=INFO < 30=WARNING < 40=ERROR < 50=CRITICAL # TODO set to INFO when done
LOGLEVELCONSOLE = logging.PERF
# two hours ahead while german summertime active, 1 otherwise
LOGTIMEOFFSET = 2
LOGPATH = "./logs/"
LOGSUFFIX = (datetime.now()+timedelta(hours=LOGTIMEOFFSET)
             ).strftime("%Y-%m-%d_%H:%M:%S")


# enable logging
if not os.path.exists(LOGPATH):
    os.makedirs(LOGPATH)

logging.basicConfig(filename=LOGPATH+LOGSUFFIX+".log",
                    filemode='w',
                    level=LOGLEVEL,
                    format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")

logging.addLevelName(logging.PERF, "PERF")
logging.Logger.perf = partialmethod(logging.Logger.log, logging.PERF)
logging.perf = partial(logging.log, logging.PERF)

console = logging.StreamHandler()
console.setLevel(LOGLEVELCONSOLE)
console.setFormatter(logging.Formatter(
    "%(name)-12s: %(levelname)-8s %(message)s"))
logging.getLogger("").addHandler(console)

logging.debug("Logger started")

new_round_event = asyncio.Event()

servicestatusnum2string = dict()
servicestatusnum2string[0] = "Unchecked"
servicestatusnum2string[1] = "Ok"
servicestatusnum2string[2] = "Recovering"
servicestatusnum2string[3] = "Mumbling"
servicestatusnum2string[4] = "Down"

statics = [
    "css",
    "js",
    "webfonts",
    "img",
    "favicon.ico"
]
[app.static(f"/{static}", f"./scoreboard/{static}") for static in statics]

app.static('/data', SCOREBOARD_JSONPATH)
app.static("/", "./scoreboard/index.html")

# cache current json round unless new files are added to the folder
json_count = 0
current_round = 0


def round_from_json_name(json_name):
    try:
        return int(scoregex.search(json_name).group(1))
    except:
        return 0


@app.route("/round")
async def get_current_round(request):
    global current_round
    return response.text(str(current_round))


def calc_current_round():
    """
    Get the current round from all scoreboard json files.
    """
    global json_count
    global current_round
    global new_round_event
    print("current round", current_round)
    json_names = os.listdir(SCOREBOARD_JSONPATH)
    if len(json_names) != json_count:
        json_count = len(json_names)
        current_round = max(round_from_json_name(x) for x in json_names)
        print("new round", current_round)
        last_event = new_round_event
        new_round_event = asyncio.Event()
        last_event.set()
    return current_round


async def notify_server_started_after_five_seconds():
    while True:
        try:
            calc_current_round()
            await asyncio.sleep(5)
        except Exception as ex:
            print(ex)

app.add_task(notify_server_started_after_five_seconds())


# WEBSOCKET ENDPOINTS
@app.websocket('/reload')
async def feed(request, ws):
    global current_round
    global new_round_event
    while True:
        try:
            print("Loopin")
            await ws.send(str(current_round))
            await new_round_event.wait()
        except websockets.exceptions.ConnectionClosed as e:
            logging.info("Client closed")
            return
        except concurrent.futures._base.CancelledError as e:
            logging.info("Client not present anymore")
            return
        except Exception as e:
            logging.error(
                "Exception while handling the WS request for index.html: ", e)
            continue


if __name__ == '__main__':
    logging.info("Scoreboard starting.")
    # generate_data()
    # perfanalysis("startup", "stop")
    # calc_current_round()
    app.run(debug=SANIC_ACCESSLOG,
            access_log=SANIC_ACCESSLOG, host=HOST, port=PORT)
