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
        --context siteUn=${SITE_UN} \
        --context s3Bucket=${S3_BUCKET} \
        --context s3ObjectKey=${S3_OBJECT} \
        --context secretsMgrArn=${SECRETS_MGR_ARN} \
        --all \
        --require-approval never
fi