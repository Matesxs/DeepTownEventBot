# Deep Town Event discord bot

## Description
Bot mainly for monitoring participations in Deep Town guild events. Data are pulled using `http://dtat.hampl.space` API,
processed and stored in database. Discord guilds can subscribe to receive guild event participation reports after each event or
use command to generate it on demand. Many other command are providet for tracking performance of players, showing history stats of guilds and comparing then with each other.

## Features
* Deep Town data tracking
    * Event contribution
    * Guild stats
        * Level
        * History and stats about event contribution
        * Member stats
    * User stats
        * Level
        * Buildings
        * Reached depth
        * Current and historic guild memberships
        * History and stats about event contribution
* Event help (with manual input of event items) and calculated efficiency for them
* Automatic Q&A
* Automatic event result announcement
* Event participation leaderboards
* Event item history and stats
* Guild level leaderboards
* Game activity graphs
* Manual blacklisting of users and guilds to keep out cheaters
* Cheater reporting system
* Upgraded discord message links
* Custom help command
* Error catching module
* Module management system

## Project structure
Folders:
* config - anything that should be changed for deployment somewhere else or owner would want to modify
* core_extensions - bot modules that will load on startup by default and cant be unloaded, so they stay always loaded
* database - anything database related
    * tables - definition of tables
* extensions - bot modules, author can configure in config what modules will be loaded on startup and then control it through commands too
* features - extensions to functionality
* utils - helper functions

## Usage
### Direct run (with separated database)
1) Create config file `config.toml` in `config` folder from `config.template.toml` file and fill needed settings
2) **(optional, recommended)** Create and activate python environment
3) Install python dependencies `pip install -r requirements.txt`
4) Start bot `python bot.py`

### Docker (with separated database)
1) Create config file `config.toml` in `config` folder from `config.template.toml` file and fill needed settings
2) Build image `docker build -t <image name> .` for example `docker build -t deeptownbot:latest .`
3) Run a bot
   1) Run bot with mounting local code `docker run -d --name <name of container> -v .:/bot <image name>` for example `docker run -d --name deeptowneventbot -v .:/bot deeptownbot:latest`
   2) Run bot without mounting local code `docker run -d --name <name of container> <image name>` for example `docker run -d --name deeptowneventbot deeptownbot:latest`

### Docker (with separated database) alternative
1) Create config file `config.toml` in `config` folder from `config.template.toml` file and fill needed settings
2) Start standalone bot stack `docker compose -f docker-compose_standalone.yml up --build`

### Docker compose **(recomended)**
1) Create config file `config.toml` in `config` folder from `config.template.toml` file and fill needed settings (by default database string is set for this method)
2) Start a bot stack (bot + database) `docker compose up --build`

### Development in docker
1) Create config file `config.toml` in `config` folder from `config.template.toml` file and fill needed settings
2) Start bot development stack
   1) With buildin database `docker compose watch`
   2) With external database `docker compose -f docker-compose_standalone.yml watch`