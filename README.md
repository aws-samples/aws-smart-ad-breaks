# Smart Ad Breaks

### Required parameters

- **MediaInsightsEnginePython39Layer:** ARN of the MIE Lambda layer (MediaInsightsEnginePython39Layer output of the MIE main CloudFormation stack)
- **WorkflowCustomResourceArn:** ARN of the MIE custom resource (WorkflowCustomResourceArn output of the MIE main CloudFormation stack)
- **WorkflowEndpoint:** Workflow endpoint. (APIHandlerName output of MIE Workflow API CloudFormation nested stack)
- **DataplaneEndpoint:** Dataplane endpoint (APIHandlerName output of the MIE Dataplane CloudFormation nested stack)
- **DataplaneBucket:** Bucket for the dataplane (DataplaneBucket output of the MIE main CloudFormation stack)

## Setup

```
sam build --parameter-overrides 'ParameterKey=MediaInsightsEnginePython39Layer,ParameterValue=[ARN obtained from MIE stack]'

sam deploy --guided
```

## Content Security Legal Disclaimer
The sample code; software libraries; command line tools; proofs of concept; templates; or other related technology (including any of the foregoing that are provided by our personnel) is provided to you as AWS Content under the AWS Customer Agreement, or the relevant written agreement between you and AWS (whichever applies). You should not use this AWS Content in your production accounts, or on production or other critical data. You are responsible for testing, securing, and optimizing the AWS Content, such as sample code, as appropriate for production grade use based on your specific quality control practices and standards. Deploying AWS Content may incur AWS charges for creating or using AWS chargeable resources, such as running Amazon EC2 instances or using Amazon S3 storage.

## Operational Metrics Collection
This solution collects anonymous operational metrics to help AWS improve the quality and features of the solution. Data collection is subject to the AWS Privacy Policy (https://aws.amazon.com/privacy/). To opt out of this feature, simply remove the tag(s) starting with “uksb-” or “SO” from the description(s) in any CloudFormation templates or CDK TemplateOptions.
