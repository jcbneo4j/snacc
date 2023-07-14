# SNACC
Spark Neo4j Automatic Code Creator

# Introduction

Welcome to the SNACC (pronounced 'snack') project. SNACC is a utility to automatically generate a notebook with code utilizing the [Neo4j Spark Connector](https://neo4j.com/docs/spark/current/) to provide an engineer the means to get a 'jump start' on ingesting their data into Neo4j. The concept of the utility is to drive it completely from a data model created in [Neo4j Solutions Workbench](https://cw.neo4j.solutions/). At a high-level, the steps are:

* Create the data model
* Run tool against data model
* Ingest data into Neo4j via the notebook generated from the tool
* Repeat the above for any updates to the data model

# Prerequisites

The project runs on docker compose so having docker/docker compose is necessary (tested with Docker v20.10.14/Docker Compose V2).

# Steps to follow

## Data Model
