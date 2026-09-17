"""Call the optional IAM-protected deployed API with the normal AWS credential chain.

Usage: python scripts/aws_request.py https://API.execute-api.REGION.amazonaws.com/demo/api/board --region ap-south-1
Never pass credentials as command-line arguments. Use `aws configure` or an AWS SSO profile.
"""
import argparse
import json
import urllib.request
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

parser = argparse.ArgumentParser()
parser.add_argument('url')
parser.add_argument('--region', required=True)
parser.add_argument('--member', default='you')
parser.add_argument('--body-file', help='JSON request body file; omitting it makes a GET request')
args = parser.parse_args()
body = open(args.body_file, 'rb').read() if args.body_file else b''
request = AWSRequest(method='POST' if body else 'GET', url=args.url, data=body,
                     headers={'Content-Type':'application/json','X-Demo-Member':args.member})
credentials = boto3.Session().get_credentials()
if credentials is None:
    raise SystemExit('No AWS credentials found. Configure an AWS profile or SSO session first.')
SigV4Auth(credentials.get_frozen_credentials(), 'execute-api', args.region).add_auth(request)
prepared = request.prepare()
outbound = urllib.request.Request(prepared.url, data=body or None, headers=dict(prepared.headers), method=prepared.method)
with urllib.request.urlopen(outbound, timeout=20) as response:
    print(json.dumps(json.load(response), indent=2))
