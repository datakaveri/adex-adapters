#! /bin/bash
kubectl create namespace adex-adapters
kubectl create secret generic adex-adapter-config --from-file=./secrets/config.ini -n adex-adapters
kubectl apply -f deployment.yaml 