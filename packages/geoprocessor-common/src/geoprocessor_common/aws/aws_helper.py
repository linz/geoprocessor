import json
from os import environ
from time import sleep
from typing import TYPE_CHECKING, Any, NamedTuple
from urllib.parse import urlparse

from boto3 import Session
from botocore.credentials import AssumeRoleCredentialFetcher, DeferredRefreshableCredentials, ReadOnlyCredentials
from botocore.session import Session as BotocoreSession
from geoprocessor_common.aws.aws_credential_source import CredentialSource
from linz_logger import get_log

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client
    from mypy_boto3_s3.type_defs import GetObjectOutputTypeDef
else:
    GetObjectOutputTypeDef = dict
    S3Client = dict

S3Path = NamedTuple("S3Path", [("bucket", str), ("key", str)])

aws_profile = environ.get("AWS_PROFILE")
session = Session(profile_name=aws_profile)
sessions: dict[str, Session] = {}

bucket_roles: list[CredentialSource] = []

bucket_config_path = environ.get("AWS_ROLE_CONFIG_PATH", "s3://linz-bucket-config/config.json")


def _init_roles() -> None:
    """Load bucket to roleArn mapping for LINZ internal buckets from SSM"""
    s3_client: S3Client = session.client("s3")
    bucket, key = parse_path(bucket_config_path)
    content_object: GetObjectOutputTypeDef = s3_client.get_object(Bucket=bucket, Key=key)
    file_content = content_object["Body"].read().decode("utf-8")
    json_content = json.loads(file_content)

    get_log().trace("bucket_config_load", config=bucket_config_path)

    for cfg in json_content["prefixes"]:
        bucket_roles.append(CredentialSource(**cfg))

    get_log().debug("bucket_config_loaded", config=bucket_config_path, prefix_count=len(bucket_roles))


def _get_client_creator(local_session: Session) -> Any:
    def client_creator(service_name: str, **kwargs: Any) -> Any:
        return local_session.client(service_name, **kwargs)

    return client_creator


def get_session(prefix: str) -> Session:
    """Get an AWS session to deal with an object on `s3`.

    Args:
        prefix: the `s3` object prefix (`key`)

    Raises:
        Exception: if there is no AWS role found for this prefix

    Returns:
        an AWS (boto3) session
    """
    cfg = _get_credential_config(prefix)
    if cfg is None:
        raise Exception(f"Unable to find role for prefix: {prefix}")

    current_session = sessions.get(cfg.roleArn, None)
    if current_session is not None:
        return current_session

    extra_args: dict[str, Any] = {"DurationSeconds": cfg.roleSessionDuration}

    if cfg.externalId:
        extra_args["ExternalId"] = cfg.externalId

    fetcher = AssumeRoleCredentialFetcher(
        client_creator=_get_client_creator(session),
        source_credentials=session.get_credentials(),
        role_arn=cfg.roleArn,
        extra_args=extra_args,
    )
    botocore_session = BotocoreSession()

    # pylint:disable=protected-access
    botocore_session._credentials = DeferredRefreshableCredentials(
        method="assume-role", refresh_using=fetcher.fetch_credentials
    )

    current_session = Session(botocore_session=botocore_session)
    sessions[cfg.roleArn] = current_session

    get_log().info("role_assume", prefix=prefix, bucket=cfg.bucket, role_arn=cfg.roleArn)
    return current_session


def get_session_credentials(prefix: str, retry_count: int = 3) -> ReadOnlyCredentials:
    """Attempt to get credentials for a `prefix`, retrying upto `retry_count` amount of times.

    Args:
        prefix: the `s3` object path (key)
        retry_count: number of retries. Defaults to 3.

    Raises:
        last_error: if there is still an error on the last retry

    Returns:
        an AWS credential (`access_key`, `secret_key`, `token`)
    """
    client_sts = session.client("sts")
    last_error: Exception = Exception(f"Invalid retry count: {retry_count}")
    for retry in range(1, retry_count + 1):
        try:
            # Get credentials may give differing access_key and secret_key
            credentials = get_session(prefix).get_credentials().get_frozen_credentials()
            return credentials
        except client_sts.exceptions.InvalidIdentityTokenException as e:
            get_log().warn("bucket_load_retry", retry_count=retry)
            sleep(0.5 * retry)
            last_error = e

    raise last_error


def _get_credential_config(prefix: str) -> CredentialSource | None:
    """Get the credential config (`bucket-config`) for the `prefix`.

    Args:
        prefix: the `s3` object path (key)

    Returns:
        the AWS credentials. @see `aws_credential_source.py`
    """
    get_log().debug("get_credentials_bucket_name", prefix=prefix)
    if not bucket_roles:
        _init_roles()

    for cfg in bucket_roles:
        if prefix.startswith(cfg.prefix):
            return cfg

    return None


def parse_path(path: str) -> S3Path:
    """Parse the path and split it into bucket name and key.

    Args:
        path: A S3 path.

    Returns:
        S3Path: s3_path.bucket , s3_path.key
    """
    parse = urlparse(path, allow_fragments=False)
    file_path = parse.path
    if is_s3(path):
        file_path = file_path.strip("./")
    return S3Path(parse.netloc, file_path)


def is_s3(path: str) -> bool:
    return path.startswith("s3://")
