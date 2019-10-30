#!/bin/bash -ex
./build.sh >& /dev/null

basedir=$(realpath $(dirname $0))

if [[ -d $basedir/task-test ]]; then rm -rf $basedir/task-test; fi;
mkdir $basedir/task-test
cd $basedir/task-test
unzip -q $basedir/export/lambda.zip

cd $basedir
docker run -e AWS_DEFAULT_REGION -e AWS_REGION -e AWS_ACCESS_KEY_ID \
    -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN \
    --mount type=bind,src=$basedir/task-test,target=/var/task,ro --rm \
        lambci/lambda:python3.7 index.lambda_handler "$@"
