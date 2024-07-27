#!/bin/bash
set -e

if [[ -d "infra" ]]; then
    cd infra

    echo "Deploy infra.."

    npm run cdk deploy -- \
        --context name=${APPLICATION_NAME} \
        --context accountId=${AWS_ACCOUNT_ID} \
        --context region=${AWS_REGION} \
        --context applicationTag=${APPLICATION_TAG} \
        --context emailNotification=${EMAIL_NOTIFICATION} \
        --context name=${SITE_UN} \
        --context name=${S3_BUCKET} \
        --context name=${S3_OBJECT} \
        --all \
        --require-approval never
fi