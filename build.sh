#!/bin/bash -ex
if [[ ! -d export ]]; then mkdir export; fi;
if [[ -f export/lambda.zip ]]; then rm -f export/lambda.zip; fi;
docker build --tag lambda-build-trigger:latest .
docker run --mount type=bind,src=$PWD/export,target=/export --rm lambda-build-trigger:latest cp /lambda.zip /export/
test -f export/lambda.zip
