#!/bin/bash
set -e

if [[ -d "infra" ]]; then
    cd infra

    echo "Install AWS CDK version ${CDK_VERSION}.."

    npm i -g aws-cdk@${CDK_VERSION}
    npm ci --include=dev

    echo "Synthesize infra.."

    npm run cdk synth -- \
        --quiet \
        --context name=${APPLICATION_NAME} \
        --context accountId=${AWS_ACCOUNT_ID} \
        --context region=${AWS_REGION} \
        --context applicationTag=${APPLICATION_TAG} \
        --context emailNotification=${EMAIL_NOTIFICATION} \
        --context siteUn=${SITE_UN} \
        --context s3Bucket=${S3_BUCKET} \
        --context s3ObjectKey=${S3_OBJECT}
fi