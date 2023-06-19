# adex-adapters
The source code, Docker images and deployment Yaml for Adex adapters 

# Prerequisites
1. For K8s deployment: The necessary queues and queue-exchange binding with appropriate
   routing key needs to be created in rabbitmq.
2. For K8s deployment: The namespace ``adex-adapters`` is created and  azure docker registry
   credentials as K8s secret ``gitcr`` is created  in that namespace.
3. For compose deployment: You need to login to ``ghcr.io`` docker registry
   in the machine compose is executed.

## docker-registry 

1. Login to the github registry using-
  
   ```sh
   docker login ghcr.io
   ```

2. Create K8s namepsace ``adex-adapters``
   ``` 
   kubectl create namespace adex-adapters
   ```
3. Create docker registry secret in K8s
   ```
   kubectl create secret docker-registry gitcr --docker-server=ghcr.io --docker-username=<docker-username> --docker-password=<docker-password> -n adex-adapters
   ```



# Deploy
1. Make a copy of the sample secrets directory by running the following command

  ```  
  cp -r example-secrets/secrets . 
  ```

2. Substitute appropriate values in ``secrets/config.ini``
3. For each change in ``src/`` directory, build and push docker image
   by incrementing the patch version. Use following command to build image

  ```
  ./build.sh
  ```
4. To test, use below command to bring up the adapter
  ```
  docker-compose up -d 
  ```  
5. To deploy in production (K8s), use following command
  ```
  ./k8s-deploy.sh
  ```
