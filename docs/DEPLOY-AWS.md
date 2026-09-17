# Deploy the complete browser app

This deployment serves the interface and API from the same HTTPS URL using API
Gateway HTTP API, Lambda Python 3.12, the actual Cedar engine, and DynamoDB.
The older `template.yaml` remains a separate IAM-authenticated API-only option.

**Status:** the hosted implementation is tested locally. No AWS stack has been
created by the project authoring session: no AWS credentials were connected,
and AWS's console could not be reached from that session's browser. The script
prints a **verified app URL** only after an actual deployment and live checks.

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
check the sign-in page, secure session, persisted board, matching, and unlocked
interface before printing the URL. It does not create artificial real-world
impact records. Your board starts with fictional sample people.

## Demo access

A random access code is generated locally and printed only in your terminal
after verification. It is also saved in `.errandloop-deployment.json` with owner
read/write permissions. **Do not commit or share that file.** The deployment
parameter contains only a SHA-256 digest marked `NoEcho`. Treat the digest as
sensitive too because it signs demo cookies. Runtime requests and access codes
are not logged by the app.

Share the app URL and demo code with judges through your chosen private channel.
Everyone with the code shares one board and can switch fictional seats or reset
that board. Cookies expire after 12 hours and are Secure, HttpOnly, and
SameSite=Strict. This is access control for a supervised hackathon demonstration,
not individual resident authentication. Do not enter real addresses, personal
pickup details, or use this to coordinate real strangers.

Repeated deployments from the same checkout reuse the saved code. To rotate it,
remove only `.errandloop-deployment.json` and redeploy; all old cookies will then
be invalid. Sign out clears this browser's cookie; a copied cookie remains valid
until expiry or code rotation.

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
