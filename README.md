# Streetlight data demo

This folder contains code for the demo using the streetlight data.

TODO: add information about the necessary configuration files

Starting procedure when using Docker swarm:

```bash
docker network create --driver overlay --scope=swarm streetlight_demo
docker volume create --name=streetlight_demo
docker build --tag streetlight_demo:1.2 ./demo
docker stack deploy -c docker-compose-for-swarm.yml demo
```

Starting procedure without Docker swarm

```bash
docker network create --driver bridge --scope=local streetlight_demo
docker volume create --name=streetlight_demo
docker-compose up --build --detach
```

The demo will be available at host:8000/streetlight
