#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { InfraStack } from '../lib/infra-stack';

const app = new cdk.App();

const props = {
    name: app.node.tryGetContext("name"),
    applicationTag: app.node.tryGetContext("applicationTag"),
    env: {
        account: app.node.tryGetContext("accountId"),
        region: app.node.tryGetContext("region"),
    },
    emailNotification: app.node.tryGetContext("emailNotification"),
    siteUn: app.node.tryGetContext("siteUn"),
    s3Bucket: app.node.tryGetContext("s3Bucket"),
    s3ObjectKey: app.node.tryGetContext("s3ObjectKey"),
    secretsMgrArn: app.node.tryGetContext("secretsMgrArn")
};

const fullName = `${props.applicationTag}-${props.name}`;

// Convert fullName to pascal case
// Uses ternary operator (a shorthand for if-else).
// If the current element is the first element in the array (i.e., index === 0),
// it converts the word to lowercase. If the current element is not the first
// element, it converts the first character of the word to uppercase
const pascalCaseFullName = fullName.split("-")
    .map((word, index) =>
        index === 0 ? word.toLowerCase() : word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join('');

const infraStack = new InfraStack(
    app,
    pascalCaseFullName,
    {
        ...props,
        fullName: fullName,
        pascalCaseFullName: pascalCaseFullName,
    }
);

cdk.Tags.of(infraStack).add("Customer", props.applicationTag);