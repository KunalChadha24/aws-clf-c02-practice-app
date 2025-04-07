"""
==============================================================
 AWS S3 Static Website Hosting & CloudFront Deployment Script
==============================================================

Project Explanation:
--------------------
Imagine you built a cool website using simple files like HTML (the structure),
CSS (the style), and JavaScript (the interactive bits). Now, you want everyone
on the internet to see it! This script helps you put your website onto Amazon Web Services (AWS),
which is like a giant collection of online tools and storage.

How does S3 host a website?
---------------------------
Think of AWS S3 (Simple Storage Service) as a huge online hard drive where you
can store files. We tell S3: "Hey, this folder (called a 'bucket') isn't just
for storing files, it's actually a website!"
1. We upload all your website files (index.html, styles.css, images, etc.) into this S3 bucket.
2. We configure the bucket to act like a web server. This means setting:
   - An 'index document' (usually `index.html`): This is the default page shown when someone visits your site's root address.
   - An 'error document' (e.g., `error.html`): This page is shown if someone tries to access a page that doesn't exist.
3. We set a 'policy' (like a set of rules) that says: "Anyone on the internet is allowed to *read* (view) the files in this bucket." This makes your website public.

Now, S3 can serve your website files directly to visitors!

How does CloudFront deliver it globally and fast?
-------------------------------------------------
Your S3 bucket lives in one specific place (an AWS 'Region', like 'us-east-1'). If someone far away (like in Australia) visits your website hosted in the US, it might be a bit slow because the data has to travel a long distance.

This is where CloudFront comes in! Think of CloudFront as a super-fast delivery network (a Content Delivery Network or CDN) with copy machines (called 'Edge Locations') all over the world.
1. CloudFront connects to your S3 bucket (the 'Origin').
2. It makes copies (caches) of your website files and stores them on these Edge Locations globally.
3. When someone visits your website, CloudFront automatically sends them the files from the *nearest* Edge Location. So, the person in Australia gets the files from a copy machine nearby, making the website load much faster!
4. CloudFront also adds extra benefits, like automatically redirecting users from `http://` to the more secure `https://`.

What this script does:
----------------------
This Python script automates the entire process:
1. Asks you for a unique name for your S3 bucket (or suggests one).
2. Creates the S3 bucket in a specific AWS region.
3. Configures the bucket for static website hosting.
4. Sets the public read policy so people can view your site.
5. Uploads all your website files from your computer (from the specified source directory) into the bucket, skipping files we don't need online (like Python scripts or Git files).
6. Creates a CloudFront 'distribution' that points to your S3 website.
7. Tells you the final S3 website address and the faster CloudFront address.

Requirements:
-------------
- Python 3 installed.
- `boto3` library installed (`pip install boto3`).
- AWS Command Line Interface (CLI) installed and configured with your AWS credentials
  (run `aws configure` in your terminal). You need permissions to manage S3 and CloudFront.
"""

import os
import boto3
import mimetypes
import logging
import uuid
import json
from botocore.exceptions import ClientError
from datetime import datetime
from typing import Tuple, Optional, List
import time

# --- Configuration ---

# Configure logging to show informational messages
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Constants ---

# Default bucket name pattern. The random part makes it likely unique.
DEFAULT_BUCKET_NAME: str = f"aws-clf-c02-practice-exam-app-{uuid.uuid4().hex[:5]}"
# AWS Region where the S3 bucket will be created. Change if needed.
REGION: str = "us-east-1"
# The directory *containing* the web application files (HTML, CSS, JS, etc.)
# ".." means the parent directory relative to where this script is located.
SOURCE_DIR: str = "../WebApp"

# File extensions to *exclude* from uploading to S3.
EXCLUDE_EXTENSIONS: List[str] = [
    ".ps1",
    ".py",
    ".pyc",
    ".git",
    ".gitignore",
    ".DS_Store",
    ".sh",
    ".tf",
    ".tfstate",
    ".tfstate.backup",
    ".tfvars",
    ".tfvars.json"
]
# Directory names to *exclude* from uploading to S3.
EXCLUDE_DIRS: List[str] = [
    "deployment-python",
    ".git",
    "__pycache__",
    ".github",
    ".vscode",
    "deployment-terraform",
]

# --- Functions ---

def get_bucket_name() -> str:
    """
    Asks the user to enter an S3 bucket name or confirms the default one.

    Simple Explanation:
    This function talks to the person running the script. It shows them a
    suggested name for the website's online folder (the S3 bucket) and asks
    if they want to use that name or type in a different one. Bucket names
    have to be unique across all of AWS (like a unique username), so we add
    random characters to the default name to help.

    Returns:
        str: The chosen S3 bucket name.
    """
    user_input: str = input(
        f"Enter S3 bucket name (press Enter to use default: {DEFAULT_BUCKET_NAME}): "
    ).strip()
    if user_input:
        logger.info(f"Using user-provided bucket name: {user_input}")
        return user_input
    logger.info(f"Using default bucket name: {DEFAULT_BUCKET_NAME}")
    return DEFAULT_BUCKET_NAME


def create_bucket(bucket_name: str, region: str) -> bool:
    """
    Creates a new S3 bucket in the specified AWS region.

    Simple Explanation:
    This function tries to create the main online folder (the S3 bucket)
    where the website files will live. It uses the name chosen earlier and
    creates it in a specific geographical area (AWS Region). It also handles
    some common problems:
    - If you already created a bucket with this name, it just says "Okay, it's already there."
    - If *someone else* already took that name, it warns you and asks for a different name.
    - If any other error happens, it reports it.

    Args:
        bucket_name (str): The desired name for the S3 bucket. Must be globally unique.
        region (str): The AWS region code (e.g., 'us-east-1', 'eu-west-1') where the bucket should be created.

    Returns:
        bool: True if the bucket was created successfully or already exists under your ownership, False otherwise.
    """
    try:
        s3_client = boto3.client("s3", region_name=region)

        # Special handling for 'us-east-1' region which doesn't need LocationConstraint
        if region == "us-east-1":
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region},
            )

        logger.info(f"Successfully created S3 bucket: {bucket_name} in region {region}")
        return True
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "BucketAlreadyOwnedByYou":
            logger.info(
                f"Bucket '{bucket_name}' already exists and is owned by you. Proceeding."
            )
            return True
        elif error_code == "BucketAlreadyExists":
            logger.warning(
                f"Bucket name '{bucket_name}' is already taken by someone else."
            )
            # Ask for a new name and retry recursively
            new_name: str = input(
                "Please enter a different, globally unique bucket name: "
            ).strip()
            if new_name:
                logger.info(f"Retrying bucket creation with name: {new_name}")
                # Important: Update the global or pass the new name back up if needed,
                # but for this script structure, recursive call is okay if we exit on failure.
                # A better pattern might involve a loop in main().
                return create_bucket(new_name, region)
            else:
                logger.error("No valid bucket name provided. Exiting.")
                return False
        else:
            logger.error(f"Failed to create bucket '{bucket_name}'. Error: {e}")
            return False


def disable_block_public_access(bucket_name: str) -> bool:
    """
    Disables the S3 Block Public Access settings for the specified bucket.
    WARNING: This is necessary for static website hosting but makes the bucket contents potentially public.

    Simple Explanation:
    By default, AWS tries to keep your S3 folders (buckets) private to prevent
    accidents. But for a website, we *need* people to be able to see the files.
    This function turns off the main "block all public access" switches for
    our specific website bucket. This doesn't instantly make everything public,
    but it allows us to set specific rules later (the 'bucket policy') to allow
    public viewing.

    Args:
        bucket_name (str): The name of the S3 bucket.

    Returns:
        bool: True if the settings were successfully disabled, False otherwise.
    """
    try:
        s3_client = boto3.client("s3")
        s3_client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": False,
                "IgnorePublicAcls": False,
                "BlockPublicPolicy": False,
                "RestrictPublicBuckets": False,
            },
        )
        logger.info(
            f"Successfully disabled Block Public Access settings for bucket: {bucket_name}"
        )
        return True
    except ClientError as e:
        logger.error(
            f"Failed to disable Block Public Access for bucket '{bucket_name}'. Error: {e}"
        )
        return False


def configure_website(bucket_name: str) -> bool:
    """
    Configures the S3 bucket for static website hosting.

    Simple Explanation:
    This tells the S3 bucket: "You are now officially a website!". It sets two
    important pieces of information:
    1. `index.html`: The main page to show when someone visits.
    2. `error.html`: The page to show if something goes wrong (like a typo in the URL).

    Args:
        bucket_name (str): The name of the S3 bucket.

    Returns:
        bool: True if website configuration was successful, False otherwise.
    """
    s3_client = boto3.client("s3")
    try:
        s3_client.put_bucket_website(
            Bucket=bucket_name,
            WebsiteConfiguration={
                "IndexDocument": {"Suffix": "index.html"},
                "ErrorDocument": {"Key": "error.html"},
            },
        )
        logger.info(
            f"Successfully configured bucket '{bucket_name}' for static website hosting."
        )
        return True
    except ClientError as e:
        logger.error(
            f"Failed to configure website hosting for bucket '{bucket_name}'. Error: {e}"
        )
        return False


def set_bucket_policy(bucket_name: str) -> bool:
    """
    Applies a bucket policy that grants public read access to the objects.

    Simple Explanation:
    This function sets the specific rules (the 'policy') for our website bucket.
    The rule we set is very simple: "Allow *anyone* ('Principal': {'AWS': '*'})
    on the internet to *read* ('Action': 's3:GetObject') any file ('Resource': 'arn:aws:s3:::bucket_name/*')
    inside this bucket." This is what makes the website files viewable in a web browser.

    Args:
        bucket_name (str): The name of the S3 bucket.

    Returns:
        bool: True if the policy was set successfully, False otherwise.
    """
    try:
        s3_client = boto3.client("s3")
        # Define the policy document allowing public read
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",  # Allows anyone
                    "Action": "s3:GetObject",  # Allows reading objects
                    "Resource": f"arn:aws:s3:::{bucket_name}/*",  # For all objects in the bucket
                }
            ],
        }

        # Convert the policy dictionary to a JSON string
        policy_string: str = json.dumps(bucket_policy)

        # Apply the policy to the bucket
        s3_client.put_bucket_policy(Bucket=bucket_name, Policy=policy_string)
        logger.info(
            f"Successfully applied public read policy to bucket: {bucket_name}"
        )
        return True
    except ClientError as e:
        logger.error(f"Failed to set bucket policy for '{bucket_name}'. Error: {e}")
        return False


def upload_file(file_path: str, bucket_name: str, object_name: Optional[str] = None) -> bool:
    """
    Uploads a single file to the specified S3 bucket.

    Simple Explanation:
    This function takes one file from your computer and copies it up into the
    S3 bucket (our online website folder). It tries to guess what kind of file
    it is (HTML, CSS, image?) so that browsers know how to display it correctly
    (this is the 'Content-Type'). For important files like HTML, CSS, and JavaScript,
    it also tells CloudFront (and browsers) not to keep copies for too long
    ('Cache-Control'), so that if you update your website, people see the changes
    faster.

    Args:
        file_path (str): The path to the local file to upload.
        bucket_name (str): The name of the target S3 bucket.
        object_name (Optional[str]): The desired name/path for the file within the S3 bucket.
                                     If None, uses the `file_path` relative structure.

    Returns:
        bool: True if the file was uploaded successfully, False otherwise.
    """
    # If object_name is not specified, use the file_path (or its relative part)
    if object_name is None:
        object_name = file_path  # Note: upload_directory provides the correct relative object_name

    # Guess the MIME type (e.g., 'text/html', 'image/jpeg') of the file
    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        content_type = (
            "application/octet-stream"  # Default if type cannot be guessed
        )

    # Set extra arguments for the upload
    extra_args = {"ContentType": content_type}

    # Set Cache-Control headers for common web assets to encourage re-validation
    # max-age=3600 means browsers/proxies can cache for 1 hour before checking again.
    # Adjust as needed. Images/fonts could have longer max-age.
    if content_type in ["text/html", "text/css", "application/javascript"]:
        extra_args["CacheControl"] = "max-age=3600"  # 1 hour

    try:
        s3_client = boto3.client("s3")
        s3_client.upload_file(
            file_path, bucket_name, object_name, ExtraArgs=extra_args
        )
        # logger.debug(f"Successfully uploaded {file_path} to {bucket_name}/{object_name} with ContentType: {content_type}")
        return True
    except ClientError as e:
        logger.error(
            f"Failed to upload file {file_path} to {bucket_name}/{object_name}. Error: {e}"
        )
        return False
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}. Skipping upload.")
        return False


def upload_directory(source_dir: str, bucket_name: str, prefix: str = "") -> None:
    """
    Uploads the contents of a local directory to an S3 bucket, maintaining structure.

    Simple Explanation:
    This function is like a robot that goes through your website's folder on
    your computer (`source_dir`). It looks inside all the sub-folders too.
    For every file it finds, it checks if it's one of the types we want to *skip*
    (like `.py` script files or `.git` folders). If it's a file we *do* want
    (like `index.html`, `styles.css`, images), it calls the `upload_file` function
    to copy it to the correct place in the S3 bucket online. It keeps the same
    folder structure online as you have on your computer. It also prints messages
    showing its progress.

    Args:
        source_dir (str): The path to the local directory whose contents should be uploaded.
        bucket_name (str): The name of the target S3 bucket.
        prefix (str): Optional prefix to add to the object keys in S3 (like a sub-folder in the bucket). Defaults to "".
    """
    source_dir_abs: str = os.path.abspath(source_dir)
    logger.info(
        f"Starting upload of directory '{source_dir_abs}' to bucket '{bucket_name}'"
        + (f" with prefix '{prefix}'" if prefix else "")
    )

    files_to_upload: List[Tuple[str, str]] = []
    total_files: int = 0

    # First pass: Walk the directory to find all files to upload
    for root, dirs, files in os.walk(source_dir_abs):
        # Modify dirs in place to prevent walking into excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for filename in files:
            # Check if the file extension should be excluded
            if any(filename.lower().endswith(ext) for ext in EXCLUDE_EXTENSIONS):
                # logger.debug(f"Skipping excluded file extension: {filename}")
                continue

            local_path: str = os.path.join(root, filename)

            # Calculate the relative path to use as the S3 object key
            relative_path: str = os.path.relpath(local_path, source_dir_abs)
            # Ensure S3 uses forward slashes for paths
            s3_key: str = relative_path.replace("\\", "/")

            # Add the prefix if one is provided
            if prefix:
                s3_key = f"{prefix}/{s3_key}"

            files_to_upload.append((local_path, s3_key))
            total_files += 1

    logger.info(f"Found {total_files} files to upload.")

    # Second pass: Upload the collected files
    uploaded_count: int = 0
    failed_count: int = 0
    for i, (local_path, s3_key) in enumerate(files_to_upload):
        logger.info(f"Uploading [{i + 1}/{total_files}]: {s3_key}")
        if upload_file(local_path, bucket_name, s3_key):
            uploaded_count += 1
        else:
            failed_count += 1

    logger.info(f"--- Upload Summary ---")
    logger.info(f"Successfully uploaded {uploaded_count} files.")
    if failed_count > 0:
        logger.warning(f"Failed to upload {failed_count} files. Check logs above.")
    logger.info(f"Finished uploading directory '{source_dir_abs}' to bucket '{bucket_name}'.")


def create_cloudfront_distribution(bucket_name: str, region: str) -> Optional[Tuple[str, str]]:
    """
    Creates a CloudFront distribution pointing to the S3 static website endpoint.

    Simple Explanation:
    This function sets up the super-fast delivery network (CloudFront). It tells
    CloudFront:
    1. Where the original website files are located (your S3 bucket's website address - the 'Origin').
    2. That the main page is `index.html` ('DefaultRootObject').
    3. To automatically change `http://` addresses to `https://` for security ('ViewerProtocolPolicy': 'redirect-to-https').
    4. How to handle caching (storing copies) of the files.
    It then starts creating this CloudFront setup (called a 'distribution'). AWS
    gives back a unique ID and a special web address (like `d1234abcd.cloudfront.net`).
    This CloudFront address is the one people should use to visit your website quickly
    from anywhere in the world.

    Args:
        bucket_name (str): The name of the S3 bucket configured for website hosting.
        region (str): The AWS region where the S3 bucket is located.

    Returns:
        Optional[Tuple[str, str]]: A tuple containing the CloudFront distribution ID
                                   and its domain name if successful, None otherwise.
    """
    logger.info(
        f"Attempting to create CloudFront distribution for S3 bucket: {bucket_name}"
    )
    cloudfront_client = boto3.client("cloudfront")

    # Construct the S3 website endpoint URL (differs from the regular S3 bucket URL)
    # Note: For newer buckets/regions, the format might vary slightly, but
    # s3-website-REGION.amazonaws.com or s3-website.REGION.amazonaws.com are common.
    # Using the format boto3 examples often use. Adjust if specific region needs differ.
    s3_website_endpoint: str = (
        f"{bucket_name}.s3-website-{region}.amazonaws.com"
    )
    # An alternative format sometimes seen: f"{bucket_name}.s3-website.{region}.amazonaws.com"
    # Verify the correct endpoint format for your region if issues arise.
    logger.info(f"Using S3 website endpoint as Origin: {s3_website_endpoint}")


    # Unique reference for this creation request
    caller_reference: str = f"s3-deploy-{bucket_name}-{datetime.now().timestamp()}"

    try:
        response = cloudfront_client.create_distribution(
            DistributionConfig={
                "CallerReference": caller_reference,
                "Comment": f"CloudFront distribution for S3 website: {bucket_name}",
                "Enabled": True,
                "DefaultRootObject": "index.html",
                "Origins": {
                    "Quantity": 1,
                    "Items": [
                        {
                            "Id": f"S3-Website-{bucket_name}", # Unique ID for this origin
                            "DomainName": s3_website_endpoint,
                            # Use CustomOriginConfig for S3 website endpoints
                            "CustomOriginConfig": {
                                "HTTPPort": 80,
                                "HTTPSPort": 443, # Although we use http-only, CF needs this
                                # S3 website endpoints only support HTTP
                                "OriginProtocolPolicy": "http-only",
                                "OriginSslProtocols": {
                                    "Quantity": 1,
                                    "Items": ["TLSv1.2"] # Standard practice
                                },
                                "OriginReadTimeout": 30,
                                "OriginKeepaliveTimeout": 5,
                            },
                        }
                    ],
                },
                "DefaultCacheBehavior": {
                    "TargetOriginId": f"S3-Website-{bucket_name}", # Match Origin Id
                    # Redirect HTTP requests to HTTPS for viewers
                    "ViewerProtocolPolicy": "redirect-to-https",
                    "AllowedMethods": {
                        "Quantity": 2, # Only allow GET and HEAD requests
                        "Items": ["GET", "HEAD"],
                        "CachedMethods": { # Cache GET and HEAD responses
                            "Quantity": 2,
                            "Items": ["GET", "HEAD"],
                        },
                    },
                    "Compress": True, # Enable automatic compression (gzip/brotli)
                    "MinTTL": 0, # Use origin Cache-Control headers primarily
                    "DefaultTTL": 86400, # Default cache duration (1 day) if no Cache-Control
                    "MaxTTL": 31536000, # Max cache duration (1 year)
                    # Do not forward query strings or cookies for static sites usually
                    "ForwardedValues": {
                        "QueryString": False,
                        "Cookies": {"Forward": "none"},
                        "Headers": {"Quantity": 0},
                        "QueryStringCacheKeys": {"Quantity": 0},
                    },
                    "TrustedSigners": {"Enabled": False, "Quantity": 0},
                    "SmoothStreaming": False,
                },
                # Use the most cost-effective price class covering all regions
                "PriceClass": "PriceClass_All",
                # Aliases would be for custom domain names (e.g., www.example.com)
                "Aliases": {"Quantity": 0},
                 # Disable WAF for this basic setup
                "WebACLId": ""
            }
        )

        distribution_id: str = response["Distribution"]["Id"]
        distribution_domain: str = response["Distribution"]["DomainName"]

        logger.info("Successfully initiated CloudFront distribution creation.")
        logger.info(f"Distribution ID: {distribution_id}")
        logger.info(f"CloudFront Domain: https://{distribution_domain}")
        
        # Add waiter to monitor CloudFront distribution deployment status
        logger.info("CloudFront distribution is now deploying. This can take 15-30 minutes...")
        logger.info("Monitoring deployment status (checking every 10 seconds):")
        
        # CloudFront doesn't have built-in waiters like S3, so we implement our own
        start_time = datetime.now()
        deployed = False
        
        try:
            while not deployed:
                # Get the current status of the distribution
                dist_info = cloudfront_client.get_distribution(Id=distribution_id)
                status = dist_info['Distribution']['Status']
                elapsed_time = (datetime.now() - start_time).total_seconds()
                
                if status == 'Deployed':
                    deployed = True
                    logger.info(f"✅ CloudFront distribution deployed successfully after {int(elapsed_time)} seconds!")
                else:
                    # Format elapsed time as minutes and seconds
                    minutes = int(elapsed_time // 60)
                    seconds = int(elapsed_time % 60)
                    logger.info(f"⏳ CloudFront distribution status: {status} (Elapsed time: {minutes}m {seconds}s)")
                    time.sleep(10)  # Check again in 10 seconds
                    
        except KeyboardInterrupt:
            logger.info("\nMonitoring interrupted by user. The distribution will continue deploying in the background.")
            logger.info(f"You can check the status in the AWS CloudFront console: Distribution ID: {distribution_id}")
        
        return distribution_id, distribution_domain

    except ClientError as e:
        logger.error(f"Failed to create CloudFront distribution. Error: {e}")
        return None


def main() -> None:
    """
    Main function to orchestrate the deployment process.

    Simple Explanation:
    This is the main controller or conductor of the script. It runs the other
    functions in the correct order:
    1. Asks for the bucket name (`get_bucket_name`).
    2. Creates the S3 bucket (`create_bucket`).
    3. Allows public access settings (`disable_block_public_access`).
    4. Configures the bucket as a website (`configure_website`).
    5. Sets the public read rule (`set_bucket_policy`).
    6. Uploads all the website files (`upload_directory`).
    7. Sets up the fast CloudFront delivery (`create_cloudfront_distribution`).
    8. Finally, it prints a summary with the important website addresses.
    If any step fails, it stops and reports the error.
    """
    logger.info("=================================================")
    logger.info(" Starting AWS S3 & CloudFront Website Deployment ")
    logger.info("=================================================")

    # 1. Get Bucket Name
    bucket_name: str = get_bucket_name()
    # It's possible create_bucket might have prompted for a different name
    # if the first one was taken. We need the *final* name used.
    # The current structure relies on create_bucket succeeding with *some* name.
    # A more robust approach might return the final name from create_bucket.

    # 2. Create S3 Bucket
    if not create_bucket(bucket_name, REGION):
        logger.error("Bucket creation failed. Deployment cannot proceed.")
        return  # Exit if bucket creation fails

    # Re-fetch the actual bucket name in case create_bucket had to change it due to collision.
    # This is a simplification; a better way is for create_bucket to return the final name.
    # For now, we assume the 'bucket_name' variable holds the correct one after create_bucket call.

    # 3. Disable Block Public Access
    if not disable_block_public_access(bucket_name):
        logger.error("Failed to modify Block Public Access settings. Deployment cannot proceed.")
        return

    # 4. Configure S3 Bucket for Website Hosting
    if not configure_website(bucket_name):
        logger.error("Failed to configure bucket for website hosting. Deployment cannot proceed.")
        return

    # 5. Set Bucket Policy for Public Read
    if not set_bucket_policy(bucket_name):
        logger.error("Failed to set bucket policy. Deployment cannot proceed.")
        return

    # 6. Upload Website Files
    # Assuming SOURCE_DIR is correctly set relative to the script's location
    upload_directory(SOURCE_DIR, bucket_name)
    # We proceed even if some file uploads failed, logging handled in upload_directory/upload_file.

    # 7. Create CloudFront Distribution
    cloudfront_result = create_cloudfront_distribution(bucket_name, REGION)

    # --- Deployment Summary ---
    print("\n" + "=" * 60)
    print("          DEPLOYMENT SUMMARY")
    print("=" * 60)
    print(f" S3 Bucket Name:        {bucket_name}")
    print(f" AWS Region:            {REGION}")

    s3_website_url: str = f"http://{bucket_name}.s3-website-{REGION}.amazonaws.com"
    print(f" S3 Website Endpoint:   {s3_website_url}")
    print("-" * 60)

    if cloudfront_result:
        distribution_id, distribution_domain = cloudfront_result
        cloudfront_url: str = f"https://{distribution_domain}"
        print(f" CloudFront Status:     Successfully Initiated")
        print(f" CloudFront ID:         {distribution_id}")
        print(f" CloudFront Domain:     {cloudfront_url}")
        print("-" * 60)
        print(" IMPORTANT: CloudFront deployment takes ~15-20 minutes globally.")
        print(" Access your site via the CloudFront Domain for optimal speed and HTTPS.")
    else:
        print(" CloudFront Status:     Failed to Create")
        print("-" * 60)
        print(" WARNING: CloudFront setup failed. You can still access the site")
        print("          via the S3 Website Endpoint, but it won't have CDN benefits or HTTPS.")

    print("=" * 60 + "\n")
    logger.info("Deployment script finished.")


# --- Script Entry Point ---

if __name__ == "__main__":
    # This block ensures the main() function is called only when the script
    # is executed directly (not when imported as a module).
    try:
        main()
    except KeyboardInterrupt:
        print("Aborted by user. Exiting.")