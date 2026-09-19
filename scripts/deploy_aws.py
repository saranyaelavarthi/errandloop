#!/usr/bin/env python3
"""Run in an authenticated AWS CloudShell. Never asks for AWS access keys.

Creates/updates only two named CloudFormation stacks. A random server secret
signs account sessions; it is not an AWS credential or a user password. No Docker, SAM CLI, or local Python
3.12 is required: pip downloads the Linux CPython 3.12 Cedar wheel explicitly.
"""
import argparse
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPCookieProcessor
import zipfile

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_TEMPLATE = {
    'AWSTemplateFormatVersion': '2010-09-09',
    'Description': 'Private ErrandLoop Lambda deployment artifacts',
    'Resources': {'Artifacts': {'Type': 'AWS::S3::Bucket', 'Properties': {
        'PublicAccessBlockConfiguration': {'BlockPublicAcls': True, 'IgnorePublicAcls': True,
                                          'BlockPublicPolicy': True, 'RestrictPublicBuckets': True},
        'BucketEncryption': {'ServerSideEncryptionConfiguration': [
            {'ServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}]}}}},
    'Outputs': {'Bucket': {'Value': {'Ref': 'Artifacts'}}}}


def stack_exists(client, name):
    try:
        return client.describe_stacks(StackName=name)['Stacks'][0]
    except ClientError as error:
        if error.response['Error']['Code'] == 'ValidationError' and 'does not exist' in error.response['Error']['Message']:
            return None
        raise


def deploy_stack(client, name, template, parameters=None, iam=False):
    args = {'StackName': name, 'TemplateBody': json.dumps(template),
            'Tags': [{'Key': 'Project', 'Value': 'ErrandLoop'}]}
    if parameters:
        args['Parameters'] = [{'ParameterKey': k, 'ParameterValue': v} for k, v in parameters.items()]
    if iam:
        args['Capabilities'] = ['CAPABILITY_IAM']
    existing = stack_exists(client, name)
    if existing and not any(t['Key'] == 'Project' and t['Value'] == 'ErrandLoop' for t in existing.get('Tags', [])):
        raise RuntimeError('Refusing to update an existing stack not tagged Project=ErrandLoop: ' + name)
    try:
        if existing:
            client.update_stack(**args)
        else:
            client.create_stack(**args)
    except ClientError as error:
        if 'No updates are to be performed' not in error.response['Error']['Message']:
            raise
        return existing
    deadline = time.monotonic() + 1800
    last_status = None
    while time.monotonic() < deadline:
        stack = client.describe_stacks(StackName=name)['Stacks'][0]
        status = stack['StackStatus']
        if status != last_status:
            print(name + ': ' + status, flush=True)
            last_status = status
        if status in ('CREATE_COMPLETE', 'UPDATE_COMPLETE'):
            return stack
        if status.endswith('_FAILED') or ('ROLLBACK' in status and status.endswith('_COMPLETE')):
            failures = [e.get('ResourceStatusReason', '') for e in client.describe_stack_events(StackName=name)['StackEvents'] if e['ResourceStatus'].endswith('_FAILED')]
            raise RuntimeError(name + ' failed: ' + '; '.join(failures[:4]))
        time.sleep(8)
    raise RuntimeError('Deployment is still running. Inspect the named CloudFormation stack before retrying.')


def package(destination):
    with tempfile.TemporaryDirectory() as directory:
        stage = Path(directory)
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check',
                        '--target', str(stage), '--platform', 'manylinux2014_x86_64',
                        '--implementation', 'cp', '--python-version', '3.12', '--abi', 'cp312',
                        '--only-binary=:all:', '-r', str(ROOT / 'requirements.txt')], check=True)
        shutil.copytree(ROOT / 'app', stage / 'app', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(stage.rglob('*')):
                if file.is_file() and '__pycache__' not in file.parts:
                    archive.write(file, file.relative_to(stage))


def verify(url):
    opener = build_opener()
    for attempt in range(12):
        try:
            with opener.open(url + '/', timeout=20) as response:
                if b'account-form' not in response.read():
                    raise RuntimeError('The public account page did not load.')
            with opener.open(url + '/api/health', timeout=20) as response:
                health = json.load(response)
                if health.get('mode') != 'live-groups' or health.get('policyEngine') != 'Cedar':
                    raise RuntimeError('The live-group service did not start.')
            try:
                opener.open(url + '/api/board', timeout=20)
            except HTTPError as error:
                if error.code != 401:
                    raise
            else:
                raise RuntimeError('The board must reject anonymous access.')
            with opener.open(url + '/onboarding.js', timeout=20) as response:
                if response.status != 200:
                    raise RuntimeError('The onboarding script did not load.')
            return
        except HTTPError as error:
            if error.code not in (404, 429, 502, 503, 504) or attempt == 11:
                raise RuntimeError('Live verification failed with HTTP ' + str(error.code)) from None
        except URLError:
            if attempt == 11:
                raise RuntimeError('Cannot reach deployed URL for verification.') from None
        time.sleep(5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--region', default=os.environ.get('AWS_REGION', 'ap-south-1'))
    parser.add_argument('--stack', default='errandloop-demo')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9-]{0,39}', args.stack):
        parser.error('Use a stack name starting with a letter, at most 40 letters, digits, or hyphens.')
    session = boto3.Session(region_name=args.region)
    identity = session.client('sts').get_caller_identity()
    print('Deploying to your authenticated account in ' + args.region + '.', flush=True)
    client = session.client('cloudformation')
    code = secrets.token_urlsafe(32)
    # Keep the session signing secret stable across redeployments.
    credential_file = ROOT / '.errandloop-deployment.json'
    if credential_file.exists():
        previous = json.loads(credential_file.read_text())
        if previous.get('account') == identity['Account'] and previous.get('region') == args.region and previous.get('stack') == args.stack:
            code = previous.get('session_secret') or previous['access_code']
        else:
            raise RuntimeError('Existing deployment file belongs to another target. Use a separate checkout.')
    saved = {'account': identity['Account'], 'region': args.region, 'stack': args.stack, 'session_secret': code}
    fd = os.open(credential_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w') as out:
        json.dump(saved, out)
    with tempfile.TemporaryDirectory() as directory:
        archive = Path(directory) / 'lambda.zip'
        package(archive)
        artifact_stack = deploy_stack(client, args.stack + '-artifacts', ARTIFACT_TEMPLATE)
        bucket = next(o['OutputValue'] for o in artifact_stack['Outputs'] if o['OutputKey'] == 'Bucket')
        key = 'lambda/' + hashlib.sha256(archive.read_bytes()).hexdigest() + '.zip'
        session.client('s3').upload_file(str(archive), bucket, key, ExtraArgs={'ServerSideEncryption': 'AES256'})
        template = json.loads((ROOT / 'infra/hosted.json').read_text())
        stack = deploy_stack(client, args.stack, template, {
            'CodeBucket': bucket, 'CodeKey': key,
            'AccessHash': hashlib.sha256(code.encode()).hexdigest()}, iam=True)
        url = next(o['OutputValue'] for o in stack['Outputs'] if o['OutputKey'] == 'AppUrl')
        print('Stack deployed. Checking public onboarding, Cedar health, and authentication gate...', flush=True)
        verify(url)
        print('\nVerified app URL: ' + url)
        print('Open the URL to create your group and your own account.')
        print('Private session secret saved in .errandloop-deployment.json, excluded from Git.')
        print('Cleanup instructions: docs/DEPLOY-AWS.md. AWS usage can incur charges.')


if __name__ == '__main__':
    try:
        main()
    except NoCredentialsError:
        sys.exit('No AWS session. Run this inside your signed-in AWS CloudShell; do not paste AWS keys into chat.')
    except (ClientError, RuntimeError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
