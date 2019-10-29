#!/usr/bin/env python3

""" 
    Creates a scoreboard data format which fits
    the requirements of ctftime.org.
    See https://ctftime.org/json-scoreboard-feed

    Since there is no support to display points per service,
    but for points per task, we use the cross product of
    our tasks and services and hand in that as tasks.

    This results in the following output model:
    {
        "tasks": [ 
            "Service 1: Attack", "Service 1: Defense", "Service 1: SLA", 
                    "Total Attack", "Total Defense", "Total SLA"
            "Service 2: Attack", "Service 2: Defense", "Service 2: SLA",
                    "Total Attack", "Total Defense", "Total SLA"
        ],
        "standings": [
            { "pos": 1, "team": "Team 1", "score": 100.0, 
                "taskStats": {
                    "Service 1: Attack": { "points": 1 },
                    "Service 1: Defense": { "points": 0.984 },
                    "Service 1: SLA": { "points": 1 },
                    "Service 2: Attack": { "points": 2 },
                    "Service 2: Defense": { "points": 2.984 },
                    "Service 2: SLA": { "points": 2 },
                    "Total Attack": { "points": 2 },"
                    "Total Defense": { "points": 2 },"
                    "Total SLA": { "points": 2 },"
                }
            },
            { "pos": 2, "team": "Team 2", "score": 0.548, 
                "taskStats": {
                    "Service 1: Attack": { "points": 1 },
                    "Service 1: Defense": { "points": 0.984 },
                    "Service 1: SLA": { "points": 1 },
                    "Service 2: Attack": { "points": 2 },
                    "Service 2: Defense": { "points": 2.984 },
                    "Service 2: SLA": { "points": 2 },
                    "Total Attack": { "points": 2 },"
                    "Total Defense": { "points": 2 },"
                    "Total SLA": { "points": 2 },"
                }
            },
        ]
    }
"""
import json
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, List
import jsons

# config
NOP_TEAM = "ENOOP"  # ignored

tasksuffix = ["Attack", "Defense", "SLA"]
totalprefix = "Total"


# json input model
@dataclass(frozen=True)
class ServicestatsInput:
    ServiceId: int
    AttackPoints: float
    LostDefensePoints: float
    ServiceLevelAgreementPoints: float
    ServiceStatus: int


@dataclass(frozen=True)
class TeamInput:
    Name: str
    TeamId: int
    TotalPoints: float
    AttackPoints: float
    LostDefensePoints: float
    ServiceLevelAgreementPoints: float
    ServiceDetails: Dict[str, ServicestatsInput]


@dataclass(frozen=True)
class ServiceInput:
    Name: str


@dataclass(frozen=True)
class Inputdata:
    CurrentRound: int
    Teams: List[TeamInput]
    Services: Dict[str, ServiceInput]


# json output model
@dataclass
class Points:
    points: float


@dataclass(order=True)
class Standing:
    pos: int
    team: str
    score: float
    taskStats: Dict[str, Points]


@dataclass(frozen=True)
class Outputdata:
    tasks: List[str]
    standings: List[Standing]


# loads data from file
def load(infile):
    content = None
    inputdata = None
    content = Path(infile).read_text(encoding="utf-8")
    inputdata = jsons.loads(content, Inputdata)
    return inputdata


# stores data to file
def save(outfile, outputdata, overwrite=False):
    if os.path.isfile(outfile) and not overwrite:
        raise IOError(f"File {outfile} already exists.")
    try:
        ugly_json = jsons.dumps(outputdata, indent=4, sort_keys=True)  # TODO: What's going on with json_s_
        json.loads(ugly_json)
        nice_jsone = json.dumps(json.loads(ugly_json), indent=2, sort_keys=True)

        with open(outfile, "w+", encoding="utf-8") as fh:
            fh.write(nice_jsone)
    except Exception as e:
        raise IOError(f"Exception while trying to save JSON file {Path(outfile)}: ", e)


# doing all the work
def export(infile, outfile, overwrite=False):
    inputdata = None
    outputdata = Outputdata([], [])
    services = {}  # required internal because the teams' service results per round do not contain the name

    inputdata = load(infile)

    # add tasks
    outputdata.tasks.append(totalprefix + " " + tasksuffix[0])
    outputdata.tasks.append(totalprefix + " " + tasksuffix[1])
    outputdata.tasks.append(totalprefix + " " + tasksuffix[2])
    for (serviceid, service) in inputdata.Services.items():
        services[serviceid] = service.Name
        outputdata.tasks.append(service.Name + " " + tasksuffix[0])
        outputdata.tasks.append(service.Name + " " + tasksuffix[1])
        outputdata.tasks.append(service.Name + " " + tasksuffix[2])

    i = 1
    # add standings
    for team in inputdata.Teams:
        if team.Name == NOP_TEAM:
            continue
        print(i, team.Name, int(team.TotalPoints))
        i += 1

        task_stats = {totalprefix + " " + tasksuffix[0]: Points(team.AttackPoints),
                      totalprefix + " " + tasksuffix[1]: Points(team.LostDefensePoints),
                      totalprefix + " " + tasksuffix[2]: Points(team.ServiceLevelAgreementPoints)}

        for (serviceid, servicedetails) in team.ServiceDetails.items():
            task_stats[services[serviceid] + " " + tasksuffix[0]] = Points(servicedetails.AttackPoints)
            task_stats[services[serviceid] + " " + tasksuffix[1]] = Points(servicedetails.LostDefensePoints)
            task_stats[services[serviceid] + " " + tasksuffix[2]] = Points(servicedetails.ServiceLevelAgreementPoints)

        team = Standing(-1, team.Name, team.TotalPoints, task_stats)
        outputdata.standings.append(team)

    # order standings, add position
    res = sorted(outputdata.standings, reverse=True)
    for pos, standing in enumerate(outputdata.standings):
        standing.pos = pos + 1

    save(outfile, outputdata, overwrite=overwrite)
    print("{} written.".format(outfile))


if __name__ == '__main__':
    # TODO: Parameters
    INPUT_JSON = "2019final.json"
    OUTPUT_JSON = "ctftime.json"
    infile = INPUT_JSON
    outfile = OUTPUT_JSON
    export(infile, outfile, overwrite=True)
