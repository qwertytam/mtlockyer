import { Duration, Stack, StackProps, Tags, CfnParameter } from 'aws-cdk-lib';
import { Topic } from 'aws-cdk-lib/aws-sns';
import { EmailSubscription } from 'aws-cdk-lib/aws-sns-subscriptions';
import { DockerImageCode, DockerImageFunction } from 'aws-cdk-lib/aws-lambda';
import { RetentionDays } from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

export interface InfraStackProps extends StackProps {
  applicationTag: string;
  fullName: string;
  pascalCaseFullName: string;
  emailNotification: string;
}

export class InfraStack extends Stack {
  constructor(scope: Construct, id: string, props: InfraStackProps) {
    super(scope, id, props);

    const lambdaFunction = new DockerImageFunction(this, `${props.pascalCaseFullName}SeleniumLambda`, {
      code: DockerImageCode.fromImageAsset("../src"),
      timeout: Duration.seconds(90),
      functionName: `${props.fullName}-function`,
      memorySize: 512,
      logRetention: RetentionDays.ONE_WEEK
    });

    const topic = new Topic(this, 'mtlockyer-sns-topic', {
      displayName: 'Mtlockyer SNS topic',
    });
    console.log('Log test 1');
    // const emailAddress = new CfnParameter(this, 'test@testing.gmail.com', { type: 'String' });
    console.log('Log test 2');
    // topic.addSubscription(new EmailSubscription(emailAddress.valueAsString));
    topic.addSubscription(new EmailSubscription(`${props.pascalCaseFullName}SeleniumLambda`));
    console.log('Log test 3');
    Tags.of(lambdaFunction).add("Customer", props.applicationTag);
    console.log('Log test 4');
  }
}
