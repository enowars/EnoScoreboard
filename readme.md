# EnoScoreboard

This is the scoreboard for our CTFs.

## Overview

### Backend

The backend is written in python3. 

We use a sanic webserver which static delivers the html file, some css, js, images and data (json files). A websocket connection is used to inform the client about new data.

Besides the file serving service there is some additional logic which allows first blood analysis, performance monitoring, logging, and other stuff.

### Frontend

The frontend is based on a single html page filled via vue.js. 

All necessary data are fetched via HTTP/GET requests. The websocket connection listenes for new rounds (new data).

## Configuration and Dependencies

### EnoEngine

The scoreboard relies mainly on the engine output. 

The engine will write json files to a chosen location. These files are the necessary input for the scoreboard. In conclusion the chosen location has to be reachable for the scoreboard. This can be done by sharing the file system in a self chosable way. Solutions are to run both containers on the same machine and simpley mount the volumes (see docker-compose.yml), to configure kubernetes or docker swarm suitable, to use a distributed file system (NFS, SSHFS, ...) or to write a custom script which does the data move job.

### EnoTeams

The scoreboard will try to display additional information for the playing teams. These information are offered by the registration page export interface. If these information are not reachable nothing will break.

### Config

The default value for all data is stored in the SCOREBOARD_JSONPATH constant and refers to "/data/". This can be the same location the engine is using to dump its json files. Files for the current round and older rounds are delivered without any changes. 

Additionally data with firstbloodinformation will be calculated during the CTF and results are stored there too. The file containing the team details will be located here also.

Check out app.py#config for configuration.

### Blacklisting

In worst case it may become necessary to remove a team or a service from the competition.  Services can be hidden by live editing scoreboard/css/services.css. Teams can be removed by editing scoreboard/js/scoreboard.js. However this features feel a little unhandy (see ##TODOs).

## TODOs

### Live Editing

Blacklisting and other live editing comes not very handy. An improvement would be to offer a better interface and a more solid way to avoid javascript caching. Last problem could be solved by adding version suffixes to the js file and modify the html onchange. The game masters could use the PROCFS to manage blacklisted service, blacklisted teams and other stuff like a MOTD (could be used for very important annotations or a final message). 

### Visual Components

Visualization could be improved by offering graphs. 

Maybe a flags-over-time graph for each service's TH cell.

And/or a bar chart for each teams TD cells for displaying SLA over time? The chart sliced per already calculated round and colored in the corresponding service status color for that round.

### Improve Data structure

A lot of data is not indexed. These data could be processed again by the python backend or by the a providing part. For example the teamdetails: Using a hashmap like structure with the team id or key as a name would allow access in constant effort. Since the data structures are not well indexed vue.js has to use loops to find the matching entry in those cases. Avoiding that would improve the rendering time noticeable.

### Test framework

Testing was done by hand so far. Of couse this turned out to be a problem. There should be test cases for all functionality, all possible circumstances (like missing or inconsistent input data) and security topics (like data escaping)... -> Automated tests wanted.

### Known Issues / Bugs

Firefox browser will not display border for TD cells on mouseover.

Old data should be removed when launching a fresh CTF. This process is not automated.
