# Optional Services

In this sub-directory lives the optional services linked to chip-n-scale stack. 

## /Inference (backend)

The Inference stack has 4 principales AWS resources:
- [VPC](/Inference/resources/vpc.yml): Virtual Private Cloud to host the services
- [RDS](/Inference/resources/rds.yml): a Postgres database where to store the prediction 
- [ELB](/Inference/resources/elb.yml): an elastic load balancer to distribute the prediction requests
- [ECS](/Inference/resources/elb.yml): CPU/GPU ecs instances running tersorflow/fastai serving


### Deploy (Serverless)

1. Edit **/Inference/config.yml**

<details>


```yaml
stage: production
stackName: inference-backend
region: us-east-1
bucket: my-bucket # existing s3 bucket to store deployment artifacts

tags:
  project: name-of-project
  
rds:
  name: results
  username: postgres
  password: mysecretpassword
  storage: 20
  instanceType: 'db.t2.medium'
  port: '5432'

ecs:
  availabilityZone: us-east-1a
  maxInstances: 1
  desiredInstances: 1
  keyPairName: keypair-2019
  instanceType: t2.nano # replace with a GPU instance for faster predictions (and higher costs)
  image: tensorflow/serving:latest # docker image containing your inference model built with TF Serving
  port: 8501 # Port to redirect input request (e.g 8501 for TF Serving)
  memory: 1000 # replace with the memory required by your TF Serving docker image

predictionPath: '/v1/models/your_model' # path to your model on the TF Serving docker image; don't include :predict

```
</details>

**Important**: you need to provide an existing bucket for serverless to store the cloudformation template.

2. Deploy

`sls deploy`


3. Get Info (db address, ...)

`sls info --verbose`