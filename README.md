# Chip 'n Scale: Queue Arranger

`chip-n-scale-queue-arranger` helps you run machine learning models over satellite imagery at scale. It is a collection of [AWS CloudFormation](https://aws.amazon.com/cloudformation/) templates deployed by [`kes`](http://devseed.com/kes/), lambda functions, and utility scripts for monitoring and managing the project.

![AWS components diagram](diagram.png)

## Requirements

- [`node` 8.x](https://nodejs.org/en/)
- [`yarn`](https://yarnpkg.com/en/) (or [`npm`](https://www.npmjs.com/))
- A [TensorFlow Serving Docker Image](https://www.tensorflow.org/tfx/serving/serving_basic) which accepts base64 encoded images. For a walkthrough of this process, check our [this post](https://medium.com/devseed/technical-walkthrough-packaging-ml-models-for-inference-with-tf-serving-2a50f73ce6f8).
- An [XYZ raster tile endpoint](https://docs.mapbox.com/api/maps/#maps)
- A corresponding list of tiles over the area you'd like to predict on. If you know the extent of your prediction area as [`GeoJSON`](http://geojson.org/), you can use [`geodex`](https://github.com/developmentseed/geodex), [`mercantile`](https://github.com/mapbox/mercantile), or [`tile-cover`](https://github.com/mapbox/tile-cover)
- An [AWS account](https://aws.amazon.com/) with sufficient privileges to deploy `config/cloudformation.template.yml`


## Stacks

To ease deployement and iteration, the pipeline is split in two AWS Stacks:
- [inference backend](/services/Inference)
  - RDS
  - ELB
  - VPS
  - ECS
- Prediction Lambda function (chip-n-scale)

The Inference backend can be then used by multiple prediction lambda functions.

## Deploying

1. Install node package
To create your own project, first install the `node` dependencies:

```bash
# Install and Configure serverless (https://serverless.com/framework/docs/providers/aws/guide/credentials/)
$ npm install serverless -g
$ npm install
```



2. [**Optional**] Deploy inference backend (see [/services/readme.md](/services/README.md))

```bash
$ cd services/Inference/

# Edit config.yml

$ sls deploy
```

3. Deploy prediction lambda

Then edit `config/config.yml` to configure your project.
```bash 
$ sls deploy
```

4. [**Optional**] Setup RDS db
```
Is this the first time setting up this stack? Run the following command to set up the database:

  $ yarn setup postgres://your-db-string

✨  Done in 424.62s.
```

This will return a database string to run a migration:

```sh
npm setup [DB_STRING]
```

If you'd like to confirm the everything is deployed correctly (recommended), run:

```sh
npm verify
```

This will test a few portions of the deployed stack to ensure that it will function correctly. Once you're ready, begin pushing tile messages to the SQS queue.

## Running

Once the stack is deployed, you can kick off the prediction by adding messages to the SQS queue. Each individual message will look like:

```json
{ "x": 1, "y": 2, "z": 3}
```

where `x`, `y`, and `z` specify [an individual map tile](https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames). Because pushing these messages into the queue quickly is important to running the prediction at scale, we've included a utility script to assist this process:

```sh
yarn sqs-push [tiles.txt] [https://your-queue-url]
```

 The first argument, `tiles.txt`, is a line-delimited file containing your tile indices in the format `x-y-z` and the second argument is the URL of your SQS Queue. If you have a lot of tiles to push to the queue, it's best to run this script in the background or on a separate computer.  The maximum number of simultaneous inflight SQS requests can be set with the `PROMISE_THRESHOLD` environment variable.

## Post processing

Once the processing is complete, you can pull down the stored results as a simple CSV file.

```sh
DATABASE_URL='postgres://myusername:mypassword@your-db-string.rds.amazonaws.com:5432/ResultsDB' yarn download my_csv_filename.csv
```

You can then convert that CSV file to a geojson while thresholding on per-class ML confidence. For example, if you have a binary prediction and only want to keep tiles where confidence in class index 1 was 95% or greater, use something like:

```sh
yarn convert-geojson my_csv_filename.csv my_thresholded_features.geojson --thresh_ind 1 --thresh 0.95
```

## Completion

After the prediction is complete, you should download the data from the AWS RDS database. Then it's okay to delete the stack:

```sh
yarn delete
```

## Speed, Cost, and GPU Utilization

The primary costs of running this stack come from Lambda Functions and GPU instances. The Lambdas parallelize the image downloading and database writing; The GPU instances provide the prediction capacity. To run the inference optimally, from a speed and cost perspective, these two resources need to be scaled in tandem. Roughly four scenarios can occur:
- **Lambda concurrency is much higher than GPU prediction capacity**. When too many Lambdas call the prediction endpoint at once, many of them will timeout and fail. The GPU instances will be fully utilized (good) but Lambda costs will be very high running longer and for more times than necessary. This will also hit the satellite imagery tile endpoint more times than needed. If this is happening, Lambda errors will be high, Lambda run time will be high, GPU utilization will be high, and SQS messages will show up in the dead letter queue. To fix it, lower the maximum Lambda concurrency or increase GPU capacity.
- **Lambda concurrency is slightly higher than GPU prediction capacity**. Similar to the above case, if the Lambda concurrency is slightly too high compared to GPU prediction throughput, the Lambdas will run for longer than necessary but not timeout. If this is happening, Lambda errors will be low, Lambda run time will be high, and GPU utilization will be high. To fix it, lower the maximum Lambda concurrency or increase GPU capacity.
- **Lambda concurrency is lower than GPU prediction capacity**. In this case, the Lambda monitoring metrics will look normal (low errors and low run time) but the GPU prediction instances have the capacity to predict many more images. To see this, run `yarn gpu-util [ssh key]` which will show the GPU utilization of each instance/GPU in the cluster:

```bash
$ yarn gpu-util ~/.ssh/my-key.pem
yarn run v1.3.2
$ node scripts/gpu-util.js ~/.ssh/my-key.pem
┌────────────────────────┬────────────────────────┬────────────────────────┐
│ IP Address             │ Instance Type          │ GPU Utilization        │
├────────────────────────┼────────────────────────┼────────────────────────┤
│ 3.89.130.180           │ p3.2xlarge             │ 5 %                    │
├────────────────────────┼────────────────────────┼────────────────────────┤
│ 23.20.130.19           │ p3.2xlarge             │ 2 %                    │
├────────────────────────┼────────────────────────┼────────────────────────┤
│ 54.224.113.60          │ p3.2xlarge             │ 3 %                    │
├────────────────────────┼────────────────────────┼────────────────────────┤
│ 34.204.40.177          │ p3.2xlarge             │ 12 %                   │
└────────────────────────┴────────────────────────┴────────────────────────┘
✨  Done in 3.30s.
```

To fix this, increase the number of concurrent Lambdas or decrease the GPU capacity. (Note that by default, the security group on the instances won't accept SSH connections. To use `gpu-util`, add a new rule to your EC2 security group)

- **Optimal :tada:**

High GPU utilization, low Lambda errors, and low Lambda run time. :ship:

## Motivation

Running machine learning inference at scale can be challenging. One bottleneck is that it's often hard to ingest/download images fast enough to keep a GPU fully utilized. This seeks to solve that bottleneck by parallelizing the imagery acquisition on AWS Lambda functions and running that separate from the machine learning predictions.

## Acknowledgements

- [The World Bank](https://www.worldbank.org/), [Nethope](https://nethope.org/), and [UNICEF](https://www.unicef.org/) partnered with us on machine learning projects that provided opportunities to test these capabilities.
- [Digital Globe](https://www.digitalglobe.com/) assisted in using their services to access ultra high-resolution satellite imagery at scale.
- [Azavea's](https://www.azavea.com/) [raster-vision-aws](https://github.com/azavea/raster-vision-aws) repo provides the base AMI for these EC2 instances (`nvidia-docker` + ECS enabled).
