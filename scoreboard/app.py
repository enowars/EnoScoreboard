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
import jsons

import socket
import concurrent
import websockets
import requests
import logging
from datetime import datetime, timedelta

import asyncio
# TODO importe bereinigen



# config
HOST = "0.0.0.0"
PORT = 8000

SCOREBOARD_JSONPATH = "/data/"
SCOREBOARD_JSON = SCOREBOARD_JSONPATH + "scoreboard.json"
SCOREBOARD_FIRSTBLOOD = SCOREBOARD_JSONPATH + "scoreboard_firstblood.json"
JSON_UPDATE_INTERVAL = 180  # [s], fitting the engine frequency, to warn on input delay
LASTROUNDINDICATOR = 1 # 0 for filenames, 1 for SCOREBOARD_JSON.data

SERVICES_CSS = "css/services.css"

scoreboard_inputfilename_regex = re.compile("scoreboard([0-9]+).json")

app = Sanic(__name__)
app.config['REQUEST_TIMEOUT'] = 30
app.config['KEEP_ALIVE'] = True
app.config['KEEP_ALIVE_TIMEOUT'] = 30
app.config['GRACEFUL_SHUTDOWN_TIMEOUT'] = 5

# TODO der accesslog koennte vom format her noch angeglichen werden. sanic nutzt auch falsche zeit, offset fehlt
SANIC_ACCESSLOG = False
SANIC_DEBUG = False

logging.PERF = 5                       # define custom log level
# LOGLEVEL must be <= LOGLEVELCONSOLE, otherwise LOGLEVELCONSOLE will be behave being on height of LOGLEVEL
LOGLEVEL = logging.INFO
# possible values: 0=NOTSET < 5=PERF < 10=DEBUG < 20=INFO < 30=WARNING < 40=ERROR < 50=CRITICAL # TODO set to INFO when done
LOGLEVELCONSOLE = logging.INFO
# two hours ahead while german summertime active, 1 otherwise
LOGTIMEOFFSET = 2
LOGPATH = "./logs/"
LOGSUFFIX = (datetime.now()+timedelta(hours=LOGTIMEOFFSET)
             ).strftime("%Y-%m-%d_%H:%M:%S")
# TODO alle configvariablen kommentieren



# static files for webserver
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



# enable logging
if not os.path.exists(LOGPATH):
    os.makedirs(LOGPATH)

logging.basicConfig(filename=LOGPATH+LOGSUFFIX+".log",
                    filemode='w',
                    level=LOGLEVEL,
                    format="%(asctime)s %(name)-21s %(levelname)-8s %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")

logging.addLevelName(logging.PERF, "PERF")
logging.Logger.perf = partialmethod(logging.Logger.log, logging.PERF)
logging.perf = partial(logging.log, logging.PERF)

console = logging.StreamHandler()
console.setLevel(LOGLEVELCONSOLE)
console.setFormatter(logging.Formatter(
    "%(name)-21s: %(levelname)-8s %(message)s"))
logging.getLogger("").addHandler(console)

logging.debug("Logger started")



# json input model
@dataclass(frozen=True)
class Servicestats_input:
    ServiceId: int
    AttackPoints: float
    LostDefensePoints: float
    ServiceLevelAgreementPoints: float
    ServiceStatus: int

@dataclass(frozen=True)
class Team_input:
    Name: str
    TeamId: int
    TotalPoints: float
    AttackPoints: float
    LostDefensePoints: float
    ServiceLevelAgreementPoints: float
    ServiceDetails: Dict[str, Servicestats_input]

@dataclass(frozen=True)
class Service_input:
    Name: str

@dataclass(frozen=True)
class Jsoninputdata:
    CurrentRound: int
    Teams: List[Team_input]
    Services: Dict[str, Service_input]

#json firstblood model
@dataclass
class Service_firstblood:
    TeamName: str # can be a concatination of team names
    Round: int

@dataclass
class Firstblooddata:
    CurrentRound: int
    IsComplete: bool
    Services: Dict[int, Service_firstblood]



# service status num to string mapping
servicestatusnum2string = dict()
servicestatusnum2string[0] = "Unchecked"
servicestatusnum2string[1] = "Ok"
servicestatusnum2string[2] = "Recovering"
servicestatusnum2string[3] = "Mumbling"
servicestatusnum2string[4] = "Down"



# global variables
new_round_event = asyncio.Event()
json_count = 0
current_round = 0
firstblooddata = Firstblooddata(-1, False, dict())



# performance analysis
perftimes = dict()
def perfanalysis(str, action):
    if action == "start":
        perftimes[str+"_1_start"] = time.perf_counter()
        perftimes[str+"_2_start"] = time.process_time()
    elif action == "stop":
        perftimes[str+"_1_stop"] = time.perf_counter()
        perftimes[str+"_2_stop"] = time.process_time()
        logging.perf(f"[{str}] Elapsed time: %.5f[ms]" % ((perftimes[str+"_1_stop"]-perftimes[str+"_1_start"])*1000))
        logging.perf(f"[{str}] CPU process time: %.5f[ms]" % ((perftimes[str+"_2_stop"]-perftimes[str+"_2_start"])*1000))
    else:
        logging.critical(f"Invalid value for parameter action: " + action)
        raise InputError("Invalid value for parameter action")



# returns content of json files
def readjsoninput(round=None):
    try:
        if round == None:
            return Path(SCOREBOARD_JSON).read_text()
        else:
            return Path(SCOREBOARD_JSON.split('.')[-2] + str(round) + '.json').read_text()
    except Exception as e:
        if round == None:
            logging.error(f"Exception while trying to read JSON file {Path(SCOREBOARD_JSON)}: " + str(e))
        else:
            logging.error(f"Exception while trying to read JSON file {Path(SCOREBOARD_JSON)}:" + str(e))



# determinates the current round, fires an event if there's a new round
def update_current_round():
    global current_round
    global new_round_event
    global json_count
    global LASTROUNDINDICATOR

    perfanalysis("used time for determinating new round", "start")
    last_round = current_round

    logging.info(f"current round: {current_round}")

    def round_from_json_name(json_name):
        try:
            return int(scoreboard_inputfilename_regex.search(json_name).group(1))
        except:
            return 0

    if LASTROUNDINDICATOR == 0:
        json_names = os.listdir(SCOREBOARD_JSONPATH)
        if len(json_names) != json_count:
            json_count = len(json_names)
            current_round = max(round_from_json_name(x) for x in json_names)
    elif LASTROUNDINDICATOR == 1:
        try:
            perfanalysis("parsing json input", "start")
            jsondata = jsons.loads(readjsoninput(), Jsoninputdata) # takes up to 500ms
            perfanalysis("parsing json input", "stop")
            current_round = jsondata.CurrentRound
        except Exception as e:
            LASTROUNDINDICATOR = 0 # fallback
            update_current_round()
            return
    else:
        logging.critical("Invalid value for constant LASTROUNDINDICATOR: " + LASTROUNDINDICATOR)
        raise InputError("Invalid value for constant LASTROUNDINDICATOR")

    if current_round > last_round:
        logging.info(f"new input data detected, new round: {current_round}")
        last_event = new_round_event
        new_round_event = asyncio.Event()
        last_event.set()

    perfanalysis("used time for determinating new round", "stop")
    return



# loads already calculated firstblood data
def load_firstblood():
    global firstblooddata
    global current_round

    perfanalysis("used time for loading firstblood: checking current state", "start")
    try:
        if os.path.isfile(Path(SCOREBOARD_FIRSTBLOOD)):
            firstblooddata = jsons.loads(Path(SCOREBOARD_FIRSTBLOOD).read_text(), Firstblooddata)
    except Exception as e:
        logging.error(f"Exception while trying to load and work on file {Path(SCOREBOARD_FIRSTBLOOD)}: " + str(e))

    if (current_round < firstblooddata.CurrentRound):
        try:
            os.remove(Path(SCOREBOARD_FIRSTBLOOD))
            logging.warning(f"removed firstblood file {Path(SCOREBOARD_FIRSTBLOOD)}, because currentfirstbloodround > current_round")
            return
        except Exception as e:
            logging.error(f"removing firstblood file {Path(SCOREBOARD_FIRSTBLOOD)} failed (oldfirstbloodround > current_round): " + str(e))
            return

    perfanalysis("used time for loading firstblood: checking current state", "stop")



# write firstblood data to disk
def store_firstblood():
    global firstblooddata
    global current_round

    perfanalysis("used time for calculating firstblood: storing results", "start")
    try:
        ugly_json = jsons.dumps(firstblooddata, indent=4, sort_keys=True)
        json.loads(ugly_json)
        nice_json = json.dumps(json.loads(ugly_json), indent=2, sort_keys=True)

        with open(SCOREBOARD_FIRSTBLOOD, "wt+", encoding="utf-8") as f:
            f.write(nice_json)
        logging.info("updating firstblood file successfull")
    except Exception as e:
        logging.error(f"Exception while trying to save JSON file {Path(SCOREBOARD_FIRSTBLOOD)}: " + str(e))
    perfanalysis("used time for calculating firstblood: storing results", "stop")



# updates the firstblood data
def update_firstblood():
    global firstblooddata
    global current_round

    # find firstbloods
    try:
        perfanalysis("used time for calculating firstblood: searching new data", "start")
        logging.info("last calculated firstblood round: " + str(firstblooddata.CurrentRound))
        if (firstblooddata.CurrentRound > current_round+10):
            logging.info("catching up may take a moment...")

        # parse every missing round for firstbloods
        for i in range (firstblooddata.CurrentRound+1, current_round+1):
            logging.info(f"checking previous round {i} for firstbloods")
            jsoninputdata = jsons.loads(readjsoninput(i), Jsoninputdata)

            for team in jsoninputdata.Teams:
                for (key, service) in team.ServiceDetails.items():

                    if service.ServiceId not in firstblooddata.Services:
                        firstblooddata.Services[service.ServiceId] = Service_firstblood("", i)

                    if firstblooddata.Services[service.ServiceId].Round == i:
                        if service.AttackPoints > 0:
                            firstblooddata.Services[service.ServiceId].TeamName += team.Name+", "

            # check whether firstblood collection is complete
            iscomplete = True
            for (key, service) in firstblooddata.Services.items():
                if service.TeamName == "":
                    iscomplete = False
            firstblooddata.IsComplete = iscomplete

            # postprocess data
            for (key, service) in list(firstblooddata.Services.items()):
                if firstblooddata.Services[key].TeamName == "":
                    del firstblooddata.Services[key]
                elif firstblooddata.Services[key].TeamName.endswith(", "):
                    firstblooddata.Services[key].TeamName = firstblooddata.Services[key].TeamName[:-2]
            firstblooddata.CurrentRound = jsoninputdata.CurrentRound

            if firstblooddata.IsComplete:
                break
        perfanalysis("used time for calculating firstblood: searching new data", "stop")

    except Exception as e:
        logging.error(f"Exception while trying to load and work on JSON file {Path(SCOREBOARD_FIRSTBLOOD)}: " + str(e))
        return

    store_firstblood()



# loops, monitores input data and updates current round
async def scoreboard_loop():
    while True:
        try:
            update_current_round()
            await asyncio.sleep(5)
        except Exception as e:
            logging.error("scoreboard loop crashed: " + str(e))
app.add_task(scoreboard_loop())



# loops, waits for a new round, updates firstblood information then
async def firstblood_loop():
    global firstblooddata
    global new_round_event
    global current_round

    if not os.path.exists(SCOREBOARD_FIRSTBLOOD):
        store_firstblood()

    while not os.path.exists(SCOREBOARD_JSON):
        await asyncio.sleep(30)

    load_firstblood()
    if firstblooddata.CurrentRound < current_round and not firstblooddata.IsComplete:
        update_firstblood()
    while True:
        if firstblooddata.IsComplete:
            logging.info("firstblood data completed, exiting task")
            return
        else:
            try:
                await new_round_event.wait()
                update_firstblood()
            except Exception as e:
                logging.error("firstblood loop crashed: " + str(e))
app.add_task(firstblood_loop())



# prepares service specific css
@app.middleware('before_server_start')
async def create_servicecss(app, loop):

    loc = os.path.dirname(__file__)+"/"+SERVICES_CSS
    jsondata = []

    try:
        while not os.path.exists(SCOREBOARD_JSON):
            await asyncio.sleep(30)
        jsondata = jsons.loads(readjsoninput(), Jsoninputdata)
    except Exception as e:
        logging.error("Input JSON missing/not valid: " + str(e))
        return

    try:
        with open(loc, "at+") as f:
            f.seek(0)
            content = f.readlines()
            missingservices = dict(jsondata.Services.items())

            for line in content:
                for serviceid, service in jsondata.Services.items():
                    if service.Name in line:
                        missingservices.pop(serviceid, None)

            for serviceid, service in missingservices.items():
                f.write(
                    f"""
.service-{service.Name} {{
        /* display: none; */
}})
                    """
                )
                logging.info("added missing css class for service " + service.Name)
            f.close()
    except Exception as e:
        logging.error("Error handling service specific css: " + str(e))
app.register_listener(create_servicecss, 'before_server_start')



# websocket endpoint
@app.websocket('/reload')
async def feed(request, ws):
    global current_round
    global new_round_event
    logging.info("Websocket client opened")
    while True:
        try:
            logging.info("Sending current round to Websocket client")
            await ws.send(str(current_round))
            await new_round_event.wait()
        except websockets.exceptions.ConnectionClosed as e:
            logging.info("Websocket client closed")
            return
        except concurrent.futures._base.CancelledError as e:
            logging.info("Websocket client not present anymore")
            return
        except Exception as e:
            logging.error(
                "Websocket connection /reload raised unexpected exception: " + str(e))
            return



if __name__ == '__main__':
    logging.info("Scoreboard starting.")
    app.run(debug=SANIC_ACCESSLOG, access_log=SANIC_ACCESSLOG, host=HOST, port=PORT)
