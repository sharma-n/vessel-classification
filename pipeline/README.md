# Pipeline

At present there are three different pipelines, which have the following functions:

* **features**

    - generate features for the neural net
    - find vessel encounters

* **anchorages** -- find anchorage locations

* **aisAnnotator*** -- attach results from neural net inference to existing AIS data


## Summary of Requirements

* A JVM.
* [SBT](http://www.scala-sbt.org/), a Scala build tool.
* A proto3-compatible version of protoc. See: 
  [protocol buffers](https://developers.google.com/protocol-buffers/).
* [Google Compute Engine](https://console.cloud.google.com) access 
  and [SDK](https://cloud.google.com/sdk) installed locally.


## SBT

The various projects are built using the Scala build tool `sbt`. SBT has a
repl, which can be entered using by running the `sbt` command in the
`pipeline` directory. Some useful SBT commands:

* To list projects: `projects`
* To select a project `project NAME`
* To compile: `compile`.
* To run: `run`.
* To test: `test`.
* To autoformat the code before check-in: `scalafmt`.
* To generate html Scaladoc: `doc`.

SBT uses maven to handle it's dependencies. So the first time you attempt a
build your machine may take some time to download all the required libraries.


## Running jobs

Jobs are started by invoking `sbt`, selecting the correct project, then invoking
run with the correct parameters. For example:

     $ sbt
     > project PROJECT_NAME
     > run ...


### Examples

**Features**

    sbt features/"run  --env=dev --experiments=shuffle_mode=service --maxNumWorkers=200 --job-name=hour_features --generate-model-features=true --generate-encounters=true --anchorages-root-path=gs://world-fishing-827/data-production/classification/release-0.1.0/pipeline/output --minRequiredPositions=100 --job-config=feature-pipeline/config/standard_config.yaml" 


**Encounters**

    > project features
    > run  --env=dev --zone=us-central1-f --experiments=shuffle_mode=service --maxNumWorkers=200 --job-name=encounters --generate-model-features=false --generate-encounters=true --anchorages-root-path=gs://world-fishing-827/data-production/classification/release-0.1.0/pipeline/output --minRequiredPositions=3 --data-years=2016

    sbt features/"run  --env=dev --zone=us-central1-f --experiments=shuffle_mode=service --maxNumWorkers=200 --job-name=encounters-vms-ais-2014-2017_9-22-2017 --generate-model-features=false --generate-encounters=true --minRequiredPositions=3 --job-config=feature-pipeline/config/joint_indo_vms_config.yaml"

sbt features/'run  --env=dev --zone=us-central1-f --experiments=shuffle_mode=service --maxNumWorkers=200 --job-name=encounters-vms-ais-2014-2017_6-14-2017 --generate-model-features=false --generate-encounters=true --job-config=feature-pipeline/config/vms_config.yaml'


**Anchorages**

    > project anchorages
  
  TODO: add current anchorages command

**Annotation**

    > project aisAnnotator
    > run --job-config=ais-annotator/config/2015_annotation.yaml --env=dev --job-name=2015_run --maxNumWorkers=100 --diskSizeGb=100 --only-fishing --workerMachineType=n1-highmem-4