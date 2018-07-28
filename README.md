# Distributed-tensorflow
This repo is designed to build a distributed tensorflow server on a kubernetes cluster. The repo consists of:
- auto generation of tf server yaml files
- mapping of worker server with the master server
- creation of a master tensorflow server interface

Docker Images in this repo are:
- "tensorflow/tf_grpc_test_server" for worker and parameter server
- "tensorflow/tensorflow" for master server
- "jupyter/minimal" for light weight jupyter notebook application
- "redis" for stateful storage

## Instruction

`
minikube start
kubectl cluster-info
python k*s_tensorflow_deployment_script.py ... [-flags] > tf_worker_ps_deployment.yaml
kubectl create -f tf_worker_ps_deployment.yaml 
`