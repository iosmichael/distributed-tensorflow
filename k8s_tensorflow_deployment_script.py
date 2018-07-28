#!/usr/bin/python
# Copyright 2016 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Generates YAML configuration files for distributed Tensorflow workers.
The workers will be run in a Kubernetes (k8s) container cluster.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import sys


DEFAULT_DOCKER_IMAGE = 'tensorflow/tf_grpc_test_server'
DEFAULT_PORT = 2222

# worker templates for yaml file generation
worker_deployment_template = (
"""
apiVersion: v1
kind: ReplicationController
metadata:
  name: tf-worker-{worker_id}
spec:
  replicas: 1
  template:
    metadata:
      labels:
        tf-worker: "{worker_id}"
    spec:
      containers:
      - name: tf-worker-{worker_id}
        image: {docker_image}
        args:
          - --cluster_spec={cluster_spec}
          - --job_name=worker
          - --task_id={worker_id}
        ports:
        - containerPort: {port}
""")

worker_service_template = (
"""apiVersion: v1
kind: Service
metadata:
  name: tf-worker-{worker_id}
  labels:
    tf-worker: "{worker_id}"
spec:
  ports:
  - port: {port}
    targetPort: {port}
  selector:
    tf-worker: "{worker_id}"
""")

worker_load_balancer_template = (
"""apiVersion: v1
kind: Service
metadata:
  name: tf-worker-{worker_id}
  labels:
    tf-worker: "{worker_id}"
spec:
  type: LoadBalancer
  ports:
  - port: {port}
  selector:
    tf-worker: "{worker_id}"
---

""")

ps_deployment_template = (
"""apiVersion: v1
kind: ReplicationController
metadata:
  name: tf-ps-{param_server_id}
spec:
  replicas: 1
  template:
    metadata:
      labels:
        tf-ps: "{param_server_id}"
    spec:
      containers:
      - name: tf-ps-{param_server_id}
        image: {docker_image}
        args:
          - --cluster_spec={cluster_spec}
          - --job_name=ps
          - --task_id={param_server_id}
        ports:
        - containerPort: {port}
---

""")

ps_service_template = (
"""apiVersion: v1
kind: Service
metadata:
  name: tf-ps-{param_server_id}
  labels:
    tf-ps: "{param_server_id}"
spec:
  ports:
  - port: {port}
  selector:
    tf-ps: "{param_server_id}"
---

""")


def main():
  """Do arg parsing."""
  parser = argparse.ArgumentParser()
  parser.add_argument('--num_workers',
                      type=int,
                      default=2,
                      help='num of worker pods running in k8s cluster')
  parser.add_argument('--num_parameter_servers',
                      type=int,
                      default=1,
                      help='num of parameter pods running in k8s cluster')
  parser.add_argument('--grpc_port',
                      type=int,
                      default=DEFAULT_PORT,
                      help='GRPC server port with a default port: %d' % DEFAULT_PORT)
  parser.add_argument('--request_load_balancer',
                      type=bool,
                      default=False,
                      help='To request worker0 to be exposed on a public IP '
                      'address via an external load balancer, enabling you to '
                      'run client processes from outside the cluster')
  parser.add_argument('--docker_image',
                      type=str,
                      default=DEFAULT_DOCKER_IMAGE,
                      help='Override default docker image for the TensorFlow '
                      'GRPC server')

  args = parser.parse_args()

  if args.num_workers <= 0:
    sys.stderr.write('--num_workers must be greater than 0; received %d\n'
                     % args.num_workers)
    return

  if args.num_parameter_servers <= 0:
    sys.stderr.write(
        '--num_parameter_servers must be greater than 0; received %d\n'
        % args.num_parameter_servers)
    return

  # Generate contents of yaml config
  yaml_config = script(args.num_workers,
                       args.num_parameter_servers,
                       args.grpc_port,
                       args.request_load_balancer,
                       args.docker_image)
  # create file using 'python k8s_tensorflow_script.py [flags] > settings.yaml
  print(yaml_config)


'''generate script'''
def script(num_workers,
           num_param_servers,
           port,
           request_load_balancer,
           docker_image):
  config = ''
  for worker_id in range(num_workers):
    config += worker_deployment_template.format(
        port=port,
        worker_id=worker_id,
        docker_image=docker_image,
        cluster_spec=WorkerClusterSpecString(num_workers,
                                             num_param_servers,
                                             port))
    if request_load_balancer:
      config += worker_load_balancer_template.format(port=port,
                                     worker_id=worker_id)
    else:
      config += worker_service_template.format(port=port,
                                  worker_id=worker_id)

  for ps_id in range(num_param_servers):
    config += ps_deployment_template.format(
        port=port,
        param_server_id=ps_id,
        docker_image=docker_image,
        cluster_spec=cluster_spec(num_workers,
                                  num_param_servers,
                                  port))
    config += ps_service_template.format(port=port,
                                      param_server_id=ps_id)

  return config

'''generate cluster specification and allow workers 
and parameter servers to communicate with each other'''
def cluster_spec(num_workers,
                      num_param_servers,
                      port):
  spec = 'worker|'
  for worker_id in range(num_workers):
    spec += 'tf-worker-%d:%d' % (worker_id, port)
    if worker_id != num_workers-1:
      spec += ';'

  spec += ',ps|'
  for param_server in range(num_param_servers):
    spec += 'tf-ps-%d:%d' % (param_server, port)
    if param_server != num_param_servers-1:
      spec += ';'

  return spec


if __name__ == '__main__':
  main()
