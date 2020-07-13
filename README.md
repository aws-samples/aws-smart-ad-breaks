# Smart Ad Breaks

## Setup

```
sam deploy --guided
```

### Required parameters

- **WorkflowCustomResourceArn:** ARN of the MIE custom resource (WorkflowCustomResourceArn output of the MIE main CloudFormation stack)
- **MediaInsightsEnginePython37Layer:** ARN of the MIE Lambda layer (MediaInsightsEnginePython37Layer output of the MIE main CloudFormation stack)
- **DataplaneEndpoint:** Dataplane endpoint (APIHandlerName output of the MIE Dataplane CloudFormation nested stack)
- **DataplaneBucket:** Bucket for the dataplane (DataplaneBucket output of the MIE main CloudFormation stack)
- **AdServerCloudFrontURL:** URL for the CloudFront distribution that serves ad contents (published blog content)
