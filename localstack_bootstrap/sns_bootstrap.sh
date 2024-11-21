#!/usr/bin/env bash

set -euo pipefail

echo "configuring sns"
echo "==================="
LOCALSTACK_HOST=localhost

create_topic() {
    local TOPIC_NAME_TO_CREATE=$1
    awslocal --endpoint-url=http://${LOCALSTACK_HOST}:4566 sns create-topic --name ${TOPIC_NAME_TO_CREATE}
}

create_queue "aw-active10-local-sns-activity-topic"
create_queue "aw-active10-local-activities-migrations"