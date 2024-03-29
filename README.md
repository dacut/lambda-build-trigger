# Lambda Build Trigger
Trigger a build from AWS Lambda by cloning a Git repository, writing a
timestamp to a file, committing it, and pushing the repository back to the
origin.

![Build status](https://codebuild.us-west-2.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoieUJJVXlJM3d2blpISCtNc0dDaTJkdDZhcTgrR3l1cjk3RXJiV2RDTkkzK1NCbjczU1RhNVRIZS9Nc0hJUkNNSWhGOXlKMS8yZ2xXMVp1VUY5KzVCdGV3PSIsIml2UGFyYW1ldGVyU3BlYyI6IlRsNVJkWHFJakc0RzBlYVMiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)

## Lambda event
The lambda handler (`index.lambda_handler`) expects an event dictionary with
the following elements:

* `repository_url`: The URL for the Git repository.
* `branch`: The branch to check out. Defaults to `master`.
* `author_name`: The author name to attribute to the commit. Defaults to
  `lambda-build-trigger`.
* `author_email`: The author email to attribute to the commit. Defaults to
  `lambda-build-trigger@lambda.internal`.
* `timestamp_filename`: The filename to write the timestamp to. Defaults to
  `.trigger`.
* `ssh_key_parameter`: An (AWS Systems Manager Parameter Store parameter)[https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html]
  containing the SSH private key to use for accessing SSH-based Git
  respositories. **This should be a SecureString parameter.** This does not
  have a default.
