statusmappings = {
  "0": "Unchecked",
  "1": "Ok",
  "2": "Recovering",
  "3": "Mumbling",
  "4": "Down"
}

Vue.filter("twodigits", function roundPoints(points) {
      return +(Math.round(points + "e+2") + "e-2");
    });

var app = new Vue({
  el: '#app',
  data() {
    return {
      currentRound: 0,
      jsonRound: 0,
      chosenTeam: null,
      teamviewRounds: 10,
      teams: [],
      rounds: [],
      services: [],
      firstbloods: [],
      teamdetails: [],
      hasfetchedstreamdata: false,
      showinactivemessage: false,
      autoreload: true,
      orderby: "TotalPointsDesc",
      ws: null,
    }
  },

  methods: {
    // changes the hash if the goto form was used
    gotoformchanged: function () {
      location.hash = "round=" + this.currentRound
    },

    // changes the hash if the teamviewrounds form was used
    teamviewroundsformchanged: function () {
      this.parseRoute(this.currentRound)
    },

    // changes the hash if the autoreload button was toggeled; returns whole hash parameter string for togglebutton href
    changeAutoreload(value) {
      var route = location.hash.slice(1)
      var params = new URLSearchParams(route);
      params.set("autoreload", value)
      return params.toString()
    },

    // orders data structures, for any table columns asc or desc
    orderteams: function(orderby) {
      setTimeout(() => {
        document.getElementById("TeamNameAsc").classList.remove("activeorderby")
        document.getElementById("TeamNameDesc").classList.remove("activeorderby")
        for (key in this.services) {
          document.getElementById("ServiceIdAsc="+this.services[key].Name).classList.remove("activeorderby")
          document.getElementById("ServiceIdDesc="+this.services[key].Name).classList.remove("activeorderby")
          Array.from(document.getElementsByClassName("ServiceId="+this.services[key].Name)).forEach(elem => elem.classList.remove("activeorderby"))
        }
        document.getElementById("TotalPointsAsc").classList.remove("activeorderby")
        document.getElementById("TotalPointsDesc").classList.remove("activeorderby")
        Array.from(document.getElementsByClassName("TotalPoints")).forEach(elem => elem.classList.remove("activeorderby"))
        document.getElementById(orderby).classList.add("activeorderby")
        if (!(orderby.includes("TeamName")))
          Array.from(document.getElementsByClassName(orderby.replace("Asc","").replace("Desc",""))).forEach(elem => elem.classList.add("activeorderby"))
      }, 10)
      switch (orderby) {
        case "TotalPointsAsc":
          this.teams = this.teams.sort((x,y) => x["TotalPoints"] - y["TotalPoints"])
          for (key in this.rounds) {
            this.rounds[key].Teams.sort((x,y) => x["TotalPoints"] - y["TotalPoints"])
          }
          break
        case "TotalPointsDesc":
          this.teams = this.teams.sort((x,y) => y["TotalPoints"] - x["TotalPoints"])
          for (key in this.rounds) {
            this.rounds[key].Teams.sort((x,y) => y["TotalPoints"] - x["TotalPoints"])
          }
          break
        case "TeamNameAsc":
          for (key in this.rounds) {
            this.rounds[key].Teams.sort((x,y) => x["Name"].localeCompare(y["Name"]))
          }
          break
        case "TeamNameDesc":
          for (key in this.rounds) {
            this.rounds[key].Teams.sort((x,y) => y["Name"].localeCompare(x["Name"]))
          }
          break
        default:
          if (orderby.startsWith("ServiceIdAsc")) {
            id = orderby.split("=")[1]
            for (key in this.services) {
              if (this.services[key].Name === id) {
                this.teams = this.teams.sort((x,y) => x["ServiceDetails"][key]["AttackPoints"] - y["ServiceDetails"][key]["AttackPoints"])
                for (round in this.rounds) {
                  this.rounds[round].Teams = this.rounds[round].Teams.sort((x,y) => x["ServiceDetails"][key]["AttackPoints"] - y["ServiceDetails"][key]["AttackPoints"])
                }
                break
              }
            }
          } else if (orderby.startsWith("ServiceIdDesc")) {
            id = orderby.split("=")[1]
            for (key in this.services) {
              if (this.services[key].Name === id) {
                this.teams = this.teams.sort((x,y) => y["ServiceDetails"][key]["AttackPoints"] - x["ServiceDetails"][key]["AttackPoints"])
                for (round in this.rounds) {
                  this.rounds[round].Teams = this.rounds[round].Teams.sort((x,y) => y["ServiceDetails"][key]["AttackPoints"] - x["ServiceDetails"][key]["AttackPoints"])
                }
                break
              }
            }
          }
          break
      this.orderby = orderby
      }
    },

    // since rank information is not provided by engine: add them here
    rankTeams: function () {
      if (this.chosenTeam === null)
        this.orderteams("TotalPointsDesc")
      i = 1
      for (key in this.teams) {
        this.teams[key].rank = i
        i++
      }
      for (key in this.rounds) {
        i = 1;
        for (teamkey in this.rounds[key].Teams) {
          this.rounds[key]["Teams"][teamkey].rank = i
          i++
        }
      }
      if (this.chosenTeam === null)
        this.orderteams(this.orderby)
    },

    // updates vue data member
    updateScoreboard: function (currentRound, chosenTeam, rounds, firstbloods, teamdetails) {
      console.debug("updateScoreboard(currentRound="+currentRound+", chosenTeam="+chosenTeam+", rounds="+rounds+
          ", firstbloods="+firstbloods+", teamdetails="+teamdetails+") called")
      
      if (!rounds.length) {
        console.error("Error receiving data")
        return;
      }
      var json = rounds[0]
      this.chosenTeam = chosenTeam
      this.rounds = rounds
      this.teams = json["Teams"]

      for (key in blacklist) {
        this.teams = json["Teams"].filter((x) => x.Name !== blacklist[key])
        for (key in this.rounds)
          rounds[key].Teams = rounds[key].Teams.filter((x) => x.Name !== blacklist[key])
      }

      this.rankTeams()
      
      this.services = json['Services']
      this.jsonRound = json["CurrentRound"]
      this.currentRound = currentRound
      this.firstbloods = firstbloods
      this.teamdetails = teamdetails
      console.log("Info: Data received, current round is now " + this.currentRound)
    },

    // called whenever the hash changes; will trigger data fetching and updateScoreboard() afterwards
    parseRoute: function (currentRound) {
      console.debug("parseRoute(currentRound="+currentRound+") called")

      window.onhashchange = () => { }

      var params = new URLSearchParams(location.hash.slice(1))
      this.autoreload = params.get("autoreload")
      var chosenTeam = params.get("team")
      var requestedRound = params.get("round")

      if (requestedRound === null && this.autoreload === null) {
        window.location.hash += "&autoreload=true"
        this.autoreload = true
      }

      requestedRound = requestedRound ? +requestedRound : currentRound
      requestedRound = requestedRound >= 0 ? requestedRound : currentRound
      this.teamviewRounds = this.teamviewRounds == 0 ? 10 : this.teamviewRounds
      this.teamviewRounds = this.teamviewRounds >= 0 ? this.teamviewRounds : -this.teamviewRounds

      var loadRound = 0
      if (requestedRound !== null && +requestedRound <= +currentRound && !(this.autoreload)) {
        loadRound = +requestedRound
        this.autoreload = false
      } else {
        loadRound = currentRound
        if (this.autoreload == "false") {
          this.autoreload = false
        } else {
          this.autoreload = true
        }
      }

      params.set("round", loadRound)
      params.set("autoreload", this.autoreload)
      location.hash = params.toString()

      if (chosenTeam == null) {
        var roundCount = 1 // normal view is using the last round only
      } else {
        var roundCount = this.teamviewRounds // team view is unsing the last 10 (default) rounds
      }

      var firstbloods = []
      var teamdetails = []
      var roundsjsons = []

      function getFirstblood() {
        $.get("./data/scoreboard_firstblood.json", (json) => {
          firstbloods = json
        })
      }

      function getTeamdetails() {
        $.get("./data/scoreboard_teamdetails.json", (json) => {
          teamdetails = json
        })
      }

      function getJsonRecursive(i) {
        if (i >= roundCount || loadRound - i < 0) {
          console.debug("updating scoreboard now...")
          app.updateScoreboard(+currentRound, chosenTeam, roundsjsons, firstbloods, teamdetails)
          window.onhashchange = () => app.parseRoute(+currentRound)
        } else {
          console.debug("fetching data file " + (loadRound-i))
          $.get("./data/scoreboard" + (loadRound - i) + ".json", (json) => {
            roundsjsons.push(json)
            getJsonRecursive(i + 1)
          })
        }
      }

      getFirstblood()
      getTeamdetails()
      getJsonRecursive(0)
    },
  },
  created: function () {

    // enable scoreboard inactive message if no data in the first 5 seconds
    setTimeout(() => this.showinactivemessage = true, 5000)

    // if no parameters yet, then add autoreload
    if (location.hash.slice(1) < 3) {
      window.location.hash = "autoreload=true"
    }

    function connect() {

      var wsProt = "ws://"
      if (location.protocol === "https:")  {
        wsProt = "wss://"
      }
      this.ws = new WebSocket(wsProt + document.domain + ':' + location.port + '/reload')

      // servers message is the new current round. parse and 
      this.ws.onmessage = function (event) {
        // do all the work like fetching data
        app.parseRoute(event.data)

        // display we-got-data-animation
        app.hasfetchedstreamdata = true
        setTimeout(function () {
          app.hasfetchedstreamdata = false
        }, 1000)

        // register eventhandler
        window.onhashchange = () => app.parseRoute(event.data)
      }

      this.ws.onclose = function () {
        console.log("Info: WS closed. Trying to reconnect in 5 seconds")
        setTimeout(function () { connect() }, 5000);
      }

      this.ws.error = this.ws.onclose
    }
    connect()
  }
})
