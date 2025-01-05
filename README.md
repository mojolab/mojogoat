# MojoGOAT - A Graph Of All Things

## Overview

GOATs help structure information sematically by taking an ontological rather than a taxonomical approach.
In this implementation of the GOAT, we use a "quad" as the semantic structure: `<source><story><target><date>`

A set of quads can be represented as a table, a CSV, a plain delimited text, or a more complex data structure
The GOAT takes a set of quads and sets up a way to feed it into a neo4j graph database using python bindings. The graph data structure, as well as the simplified underlying quad storage can be queried using a simple REST API

## GOAT Sutras

1. You can own a GOAT, some GOATs, many GOATs, big GOATs, small GOATs, public GOATs, private GOATs and so forth but no one owns THE GOAT
2. GOATs will eat almost everything, don't feed a GOAT rubbish unless you want a sick GOAT
3. When a GOAT gets too fat, make biryani

## Set up the Docker image

[Xetrapal Docker Image](https://hub.docker.com/r/arjunvenkatraman/xetrapal)

Install Docker on your machine, then use a terminal to run the following command

```
docker pull -a arjunvenkatraman/xetrapal
```

Then start a container using the following command

```
docker run -it -p8888:8888 -p5000:5000 --mount type=bind,source=$pwd/xpal-data,target=/xpal-data --mount type=bind,source=$pwd/xpal-src,target=/xpal-src arjunvenkatraman/xetrapal:latest zsh
```

Attach a shell to the running container to get a command line

## Run a Jupyter Notebook from the docker container

```
jupyter notebook --allow-root --ip 0.0.0.0
```
Connect to the Jupyter console in a browser using the link in the command output of the form: ```http://127.0.0.1:8888/?token=<TOKEN>```

Create a new working folder under ```xpal-data``` and a new Jupyter notebook under this new folder. 


### Connect to the Neo4J database from your Jupyter Notebook

Create a ```.json``` file under ```xpal-data/conf``` with the following format

```
{
    "database":"neo4j",
    "url":"<NEO4J DB URL>",
    "password":"<NEO4J DB PASSWORD>"
}

```



Try the following code blocks





## Set up a Neo4J Free Instance

