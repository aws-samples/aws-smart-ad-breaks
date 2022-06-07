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
