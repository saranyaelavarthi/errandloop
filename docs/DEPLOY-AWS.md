# Deploy the complete browser app

This deployment serves the interface and API from the same HTTPS URL using API
Gateway HTTP API, Lambda Python 3.12, the actual Cedar engine, and DynamoDB.
The older `template.yaml` remains a separate IAM-authenticated API-only option.

**Status:** the hosted implementation is tested locally. No AWS stack has been
created by the project authoring session: no AWS credentials were connected,
and AWS's console could not be reached from that session's browser. The script
prints a **verified app URL** only after an actual deployment and live HTTP checks.

## Run from your AWS CloudShell

Sign in to your AWS account, select your desired region, and open CloudShell.
Run these commands (the example explicitly deploys in Mumbai):

```bash
git clone https://github.com/saranyaelavarthi/errandloop.git
cd errandloop
python3 scripts/deploy_aws.py --region ap-south-1
```

For an existing clone, `cd errandloop && git pull --ff-only` first instead of
cloning again. The script uses your existing AWS session; it never asks for AWS
access keys. It uses CloudShell’s preinstalled Python 3, Boto3, and pip, plus network access to PyPI. Outside CloudShell, use Python 3.10+ and install `boto3==1.43.96` first.
It downloads the Linux CPython 3.12 native Cedar wheel explicitly, so the shell
does not need Docker, SAM, or its own Python 3.12 interpreter.

The caller needs permission to manage the two CloudFormation stacks and their
S3, Lambda, API Gateway, DynamoDB, CloudWatch Logs, and IAM role resources,
including `iam:PassRole`. Organization policies or account quotas may prevent
deployment. A failed run reports the failing stack/resource reason.

The script creates `errandloop-demo-artifacts` and `errandloop-demo`. It refuses
to update existing stacks without the `Project=ErrandLoop` tag. Successful runs
check public onboarding, Cedar health, and the authentication gate before printing the URL. It does not create artificial real-world
impact records. New groups start empty, using the names and places their owners enter.

## Accounts and server sessions

The URL opens a public **Create / Join / Sign in** screen. There is no shared
login code and no sample data. Every person creates their own password-protected
account. Group owners choose their pickup locations and handover point, then
invite neighbours using the random group code shown in **Your group**.

The deployment script generates a private server signing secret. It saves it in
`.errandloop-deployment.json` with owner read/write permissions, outside Git, and
passes its digest as the masked `AccessHash` CloudFormation parameter. Despite the
legacy parameter name, this is a server signing key, not a user login password.
Do not share the deployment file. Reusing it preserves existing sessions across
redeployments; removing it before redeployment rotates the server key and logs
all users out without deleting their accounts.

Cookies expire after 12 hours and are Secure, HttpOnly, and SameSite=Strict.
Accounts have salted scrypt hashes and a temporary lockout after five incorrect
password attempts. Session identity determines both group and member; client actor
headers cannot impersonate another member. There is no password recovery, member
removal, invitation rotation, or identity verification in this initial version.

The deployment smoke check verifies onboarding assets, Cedar health, and rejection
of unauthenticated board requests. Real multi-account exchanges are covered by
local integration tests; no live cloud user-flow test has run in this environment.

## Cost and cleanup

This uses on-demand services, but **is not guaranteed free**. API throttling is
best effort, not a spending cap. Logs retain seven days; the demo table remains
until stack deletion. Watch usage in your AWS account and remove resources after
the event. No credit balance or billing alarm has been configured by this project.

To delete the demo and all its board data, run the following only when you no
longer need it. Export activity from the app first if desired:

```bash
aws cloudformation delete-stack --stack-name errandloop-demo --region ap-south-1
aws cloudformation wait stack-delete-complete --stack-name errandloop-demo --region ap-south-1
```

Then inspect the **Bucket** output of the `errandloop-demo-artifacts` stack.
Empty that exact artifact bucket in S3 (it contains only packaged Lambda builds
uploaded by this script), then delete the artifact stack. An S3 bucket containing
objects cannot be deleted by CloudFormation. If you changed `--stack` or region,
use your selected names and region for cleanup.

References: [AWS CloudShell](https://docs.aws.amazon.com/cloudshell/),
[HTTP API stages](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-apigatewayv2-stage.html),
[Lambda HTTP API integration](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html).
