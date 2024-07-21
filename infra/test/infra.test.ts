import * as cdk from 'aws-cdk-lib';
import { Template, Match } from 'aws-cdk-lib/assertions';
import * as Infra from '../lib/infra-stack';

test("Lambda Created", () => {
  const app = new cdk.App();
  // WHEN
  const stack = new Infra.InfraStack(app, "MyTestStack", {
    fullName: "test-test",
    pascalCaseFullName: "TestTest",
    applicationTag: "app-tag-test",
  });
  // THEN

  const template = Template.fromStack(stack);

  template.hasResourceProperties("AWS::Lambda::Function", {
    FunctionName: "test-test-function"
  });
});
