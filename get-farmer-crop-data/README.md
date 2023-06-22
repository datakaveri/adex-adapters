# Introduction
Adex get-farmer-data API adapter

# Prerequisites
 The necessary queues and queue-exchange binding with appropriate routing key needs to be created in rabbitmq.

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
