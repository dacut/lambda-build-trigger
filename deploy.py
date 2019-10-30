#!/usr/bin/env python3
"""
Deploy a file to one or more S3 locations.
Usage: deploy.py [options] <file> s3://<bucket>/<object> ...

Options:
    -a <acl> | --acl <acl>
        Use the specified ACL instead of public-read.

    -h | --help
        Display this help text.
"""
from base64 import b64encode
from functools import partial
from getopt import getopt, GetoptError
import hashlib
from logging import basicConfig, getLogger, DEBUG
from os.path import basename
from multiprocessing import Pool
from sys import argv, exit as sys_exit, stderr, stdout
from botocore.client import Config
import boto3

log = getLogger("deploy")

def main(args):
    """
    Main entrypoint.
    """
    basicConfig(level=DEBUG, format="%(process)5d %(asctime)s %(name)s [%(levelname)s] %(filename)s %(lineno)d: %(message)s")
    getLogger().handlers[0].formatter.default_msec_format = ".%03d"

    sts = boto3.client("sts")
    ident = sts.get_caller_identity()
    log.debug("Caller identity: %s", ident)

    ssm = boto3.client("ssm")
    result = ssm.get_parameter(Name="ping")
    
    log.debug("SSM ping: %s", result['Parameter']['Value'])

    acl = "public-read"
    try:
        opts, args = getopt(args, "a:h", ["acl=", "help"])
        for opt, val in opts:
            if opt in ("-a", "--acl",):
                acl = val
            elif opt in ("-h", "_-help"):
                usage(stdout)
                return 0
    except GetoptError as e:
        print(str(e), file=stderr)
        return 2

    if len(args) < 2:
        usage()
        return 2
    
    src = args[0]
    dests = []
    for arg in args[1:]:
        if not arg.startswith("s3://"):
            log.error("Destination must begin with s3://: %s", arg)
            return 2
        
        dest = arg[5:]
        if "/" not in dest:
            bucket = dest
            key = basename(src)
        else:
            bucket, key = dest.split("/", 1)
            if key.endswith("/") or not key:
                key += basename(src)
        
        dests.append((bucket, key))

    errors = 0
    successes = 0

    pool = Pool(len(dests))
    results = {
        (bucket, key): pool.apply_async(upload, (src, bucket, key, acl))
        for bucket, key in dests
    }

    for loc, result in results.items():
        result.wait()
        try:
            result.get()
            successes += 1
        except Exception as e:
            bucket, key = loc
            log.error(
                "Failed to upload to s3://%s/%s: %s", bucket, key, e,
                exc_info=True)
            errors += 1
    
    if errors:
        log.error(f"Deploy failed: {successes} succeeded, {errors} failed")
        return 1
    
    log.info(f"Deploy succeeded: {successes} succeeded, 0 failed")
    return 0

def upload(src, bucket, key, acl):
    """
    Multiprocessing callback for uploading the file.
    """
    s3 = boto3.client("s3", region_name="us-east-1")
    loc = s3.get_bucket_location(Bucket=bucket).get("LocationConstraint")
    if loc == "EU":
        loc = "eu-west-1"
    
    if loc:
        # Use the S3 location in the specific region
        s3 = boto3.client(
            "s3", region_name=loc, config=Config(signature_version="s3v4"))

    with open(src, "rb") as fd:
        md5 = hashlib.md5()
        sha256 = hashlib.sha256()

        while True:
            block = fd.read(65536)
            if not block:
                break
            
            md5.update(block)
            sha256.update(block)

        fd.seek(0)
        s3.put_object(
            ACL=acl, Body=fd, Bucket=bucket, Key=key,
            ContentMD5=b64encode(md5.digest()).decode("ascii"),
            Metadata={"x-amz-content-sha256": sha256.hexdigest()})

    log.info("Uploaded to s3://%s/%s", bucket, key)

def usage(fd=stderr):
    """
    Display usage information.
    """
    fd.write(__doc__.strip() + "\n")
    fd.flush()
    return

if __name__ == "__main__":
    sys_exit(main(argv[1:]))
