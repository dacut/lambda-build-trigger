#!/usr/bin/env python3
"""
Lambda handler for cloning a repository, writing the current date to a
file, committing it, and pushing it.
"""
from datetime import datetime
from logging import getLogger, DEBUG
from os import access, chmod, environ, umask, W_OK
from os.path import exists, join as path_join
from tempfile import mkdtemp, TemporaryDirectory
from typing import Any, Dict, Optional

import boto3

if (not exists("/usr/bin/git") and "LAMBDA_TASK_ROOT" in environ
    and exists(f'{environ["LAMBDA_TASK_ROOT"]}/git')):
    environ["GIT_PYTHON_GIT_EXECUTABLE"] = f'{environ["LAMBDA_TASK_ROOT"]}/git')
from git import Actor, Repo

DEFAULT_AUTHOR_NAME = "lambda-build-trigger"
DEFAULT_AUTHOR_EMAIL = "lambda-build-trigger@lambda.internal"
DEFAULT_TIMESTAMP_FILENAME = ".trigger"
BASE_SSH_COMMAND = """
ssh -oBatchMode=yes -oCheckHostIp=no -oKbdInteractiveAuthentication=no
-oPasswordAuthentication=no -oPreferredAuthentications=publickey
-oStrictHostKeyChecking=no -oUpdateHostKeys=no
""".strip().replace("\n", " ")

log = getLogger()
log.setLevel(DEBUG)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda entrypoint.
    """
    repo_url = event.get("repository_url")
    if repo_url is None:
        raise ValueError("repository_url was not specified")

    repo_branch = event.get("branch", "master")
    author_name = event.get("author_name", DEFAULT_AUTHOR_NAME)
    author_email = event.get("author_email", DEFAULT_AUTHOR_EMAIL)
    timestamp_filename = event.get(
        "timestamp_filename", DEFAULT_TIMESTAMP_FILENAME)
    author = Actor(author_name, author_email)

    ssh_key_param = event.get("ssh_key_parameter")
    if ssh_key_param is None:
        ssh_key_param = environ.get("SSH_KEY_PARAM")
    
    with TemporaryDirectory() as ssh_dir:
        if ssh_key_param is None:
            log.info(
                "No ssh_key_parameter specified; SSH key authentication will "
                "not be used.")
            ssh_key_filename = None
        else:
            log.info("Using SSH key from %s", ssh_key_param)
            ssm = boto3.client("ssm")
            result = ssm.get_parameter(Name=ssh_key_param, WithDecryption=True)
            ssh_key = result["Parameter"]["Value"]
            old_umask = umask(0o077)
            try:
                ssh_key_filename = path_join(ssh_dir, "id_rsa")
                with open(ssh_key_filename, "w") as fd:
                    fd.write(ssh_key)
            finally:
                umask(old_umask)

        run(repo_url, repo_branch, timestamp_filename, author, ssh_key_filename)
    return {}

def run(
        repo_url: str, branch: str, timestamp_filename: str, author: Actor,
        ssh_key_filename: Optional[str] = None) -> None:
    """
    Check out the repository and create or update the timestamp filename.
    """
    with TemporaryDirectory() as local_dir:
        # Initialize the repository
        log.info("Initializing local repository in %s", local_dir)
        repo = Repo.init(local_dir)

        git_ssh_command = BASE_SSH_COMMAND

        if ssh_key_filename:
            git_ssh_command += f" -oIdentityFile={ssh_key_filename}"

        log.info("Using GIT_SSH_COMMAND=%s", git_ssh_command)
        repo.git.update_environment(GIT_SSH_COMMAND=git_ssh_command)

        # Create the remote and fetch the remote branch.
        log.info("Creating remote 'origin' from URL %s", repo_url)
        origin = repo.create_remote("origin", repo_url)

        log.info("Fetching refs/heads/%s from origin", branch)
        try:
            origin.fetch(f"refs/heads/{branch}")[0]
        except Exception as e:
            log.error("Failed: %s", e, exc_info=True)
            from time import sleep
            while True:
                sleep(30)
        remote_branch = origin.refs[branch]

        # Create a local branch to track the origin branch.
        log.info("Checking out branch %s", branch)
        local_branch = repo.create_head(branch, remote_branch)
        local_branch.set_tracking_branch(remote_branch)
        local_branch.checkout()

        # Update/create the timestamp file.
        timestamp_path = path_join(local_dir, timestamp_filename)
        now = datetime.utcnow()
        now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        if exists(timestamp_path) and not access(timestamp_path, W_OK):
            chmod(timestamp_path, 0o666)

        log.info(
            "Creating timestamp file %s with timestamp %s", timestamp_path,
            now_str)
        with open(timestamp_path, "w") as fd:
            now = datetime.utcnow()
            fd.write(now_str + "\n")
        chmod(timestamp_path, 0o644)

        log.info("Adding timestamp file to the index")
        repo.index.add(timestamp_filename)

        log.info("Committing timestamp update")
        repo.index.commit(
            "Automatically update timestamp to " + now_str, author=author,
            committer=author)

        log.info("Pushing updates to remote 'origin'")
        origin.push()

        log.info("Done")
