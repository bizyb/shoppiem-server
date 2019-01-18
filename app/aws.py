import boto
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from uuid import uuid4
import yaml
config = None
with open("config.yaml") as f:
    config = yaml.safe_load(f)

aws_key, aws_secret = config.get("aws_access_key_id"), config.get("aws_secret_access_key")
def upload_file(stream, sku, mime):
    """
    Upload a file to AWS S3.

    :param stream: the input data 
    :param key: the file name
    :return url: the public url of the uploaded object 
    """
    conn = boto.connect_s3(aws_key, aws_secret)
    bucket_name = aws_key.lower() 
    directory = config.get("s3_directory")

    k = Key(conn.get_bucket(bucket_name))
    file_key = str(uuid4()).replace("-","")
    file_key = "{}/{}/{}.{}".format(directory, sku, file_key, mime)
    k.key = file_key
    k.set_metadata('Content-Type', mime)
    bytes_sent = k.set_contents_from_file(stream)

    service = "s3"
    url = "https://{}.amazonaws.com/{}/{}".format(service, bucket_name, file_key)
    print url
    print "bytes sent: ", bytes_sent
    return url  


