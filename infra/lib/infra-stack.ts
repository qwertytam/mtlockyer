import { Duration, Stack, StackProps, Tags, CfnResource, aws_iam as iam } from 'aws-cdk-lib';
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
  siteUn: string;
  s3Bucket: string;
  s3ObjectKey: string;
  secretsMgrArn: string;
}

export class InfraStack extends Stack {
  constructor(scope: Construct, id: string, props: InfraStackProps) {
    super(scope, id, props);

    const lambdaFunction = new DockerImageFunction(this, `${props.pascalCaseFullName}DIF`, {
      code: DockerImageCode.fromImageAsset("../src"),
      timeout: Duration.seconds(90),
      functionName: `${props.fullName}-function`,
      memorySize: 512,
      logRetention: RetentionDays.ONE_WEEK
    });

    const topic = new Topic(this, 'mtlockyer-sns-topic', {
      displayName: 'Mtlockyer SNS topic',
    });

    const regexPat = /,|;/;
    var emailAddresses = props.emailNotification.split(regexPat);
    emailAddresses.forEach((emailAddr, index) => {
        // Note using json format as Gmail in particular causes spam filtering issues
        // if just sending regular non-json format emails
        topic.addSubscription(new EmailSubscription(emailAddr, {json: true}));
        index++;
    });

    const schedulerRole = new iam.Role(this, "mtlockyer-scheduler-role", {
      assumedBy: new iam.ServicePrincipal("scheduler.amazonaws.com"),
     });

    var lambdaPayload:JSON = <JSON><unknown>{
      "site-un": props.siteUn,
      "s3-bucket": props.s3Bucket,
      "s3-object-key": props.s3ObjectKey,
      "sns-topic-arn": topic.topicArn,
    }

    // To run at 1 minute past the hour, every three hours
    const ebScheduler = new CfnResource(this, 'mtlockyer-scheduler', {
      type: 'AWS::Scheduler::Schedule',
      properties: {
        Name: `${props.pascalCaseFullName}EBScheduler`,
        Description: "Runs Mt Lockyer every three hours",
        FlexibleTimeWindow: { Mode: 'OFF' },
        ScheduleExpression: "rate(5 minutes)",
        Target: {
          Arn: lambdaFunction.functionArn,
          Input: JSON.stringify(lambdaPayload),
          RoleArn: schedulerRole.roleArn,
        },
      },
    });

  const invokeLambdaPolicy = new iam.Policy(this, "invoke-mtlockyer-lambda", {
    document: new iam.PolicyDocument({
     statements: [
       new iam.PolicyStatement({
         actions: ["lambda:InvokeFunction"],
         resources: [lambdaFunction.functionArn],
         effect: iam.Effect.ALLOW,
       }),
       new iam.PolicyStatement({
        actions: ["sns:Publish"],
        resources: [topic.topicArn],
        effect: iam.Effect.ALLOW,
      }),
      new iam.PolicyStatement({
        actions: ["secretsmanager:GetSecretValue"],
        resources: [props.secretsMgrArn],
        effect: iam.Effect.ALLOW,
      }),
    ],
    }),
   });
  schedulerRole.attachInlinePolicy(invokeLambdaPolicy);

  schedulerRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonS3FullAccess'));
  schedulerRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'));

  lambdaFunction.addToRolePolicy(new iam.PolicyStatement()
  .addResource(props.secretsMgrArn)
  .addAction("secretsmanager:GetSecretValue"));

  Tags.of(lambdaFunction).add("Customer", props.applicationTag);

  }
}
