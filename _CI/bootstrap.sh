#!/bin/bash
set -e

if [[ -d "infra" ]]; then
    cd infra

    echo "Install AWS CDK version ${CDK_VERSION}.."
    echo "SITE_UN '${SITE_UN}'"
    echo "S3_BUCKET '${S3_BUCKET}'"
    echo "S3_OBJECT '${S3_OBJECT}'"
    echo "emailNotification '${EMAIL_NOTIFICATION}'"

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
        --context s3ObjectKey=${S3_OBJECT} \
        --context secretsMgrArn=${SECRETS_MGR_ARN}
fi