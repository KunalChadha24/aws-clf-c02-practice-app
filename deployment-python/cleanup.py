"""
========================================================
 AWS S3 Bucket & CloudFront Distribution Cleanup Script
========================================================

Project Explanation:
--------------------
Remember how we used the other script to put your website online using AWS?
Well, sometimes you want to take the website down, maybe because you're done
with the project or you want to avoid paying for the AWS services when you're
not using them (like turning off the lights when you leave a room).

This script helps you safely remove the main things we created:
1. The CloudFront 'delivery network' that made your site fast globally.
2. The S3 'online folder' (bucket) where all your website files were stored.

Why do we need a special script?
--------------------------------
We have to remove things in the right order, like cleaning up building blocks:
- First, we need to tell CloudFront to stop delivering the website (disable it).
- Then, we wait for it to be fully stopped everywhere.
- After that, we can tell AWS to delete the CloudFront setup.
- While AWS is deleting CloudFront (which takes time!), we clean out the S3 bucket
  by deleting all the website files inside it. A bucket must be empty before
  it can be deleted.
- Finally, once the bucket is empty and CloudFront is gone, we can tell AWS to
  delete the S3 bucket itself.

How does it know *what* to delete?
----------------------------------
- You tell the script the name of the S3 bucket you want to delete.
- The script then tries to be clever: It looks through all your CloudFront setups
  to find the one that was specifically using *your* S3 bucket as its source.
  It recognizes this by looking for the bucket's special website address in the
  CloudFront settings.
- It will then ask you: "Are you sure you want to delete THIS bucket and THAT
  CloudFront distribution?" You have to confirm before it does anything dangerous.

What this script does:
----------------------
1. Asks you for the S3 bucket name you want to delete.
2. Tries to find the AWS Region where the bucket lives.
3. Searches your AWS account for a CloudFront distribution linked to that S3 bucket's website endpoint.
4. Asks for your confirmation to delete the found resources (bucket and maybe CloudFront).
5. If confirmed and a CloudFront distribution was found:
   - Disables the CloudFront distribution.
   - Waits until it's fully disabled.
   - Tells AWS to delete the CloudFront distribution.
   - Starts polling (checking every 10 seconds) until CloudFront confirms it's deleted.
6. If confirmed (and after CloudFront deletion if applicable):
   - Deletes all files (including old versions if versioning was enabled) from the S3 bucket.
   - Waits until the bucket is empty.
   - Tells AWS to delete the S3 bucket.
   - Waits until AWS confirms the bucket is gone.
7. Reports the success or failure of each step.

Requirements:
-------------
- Python 3 installed.
- `boto3` library installed (`pip install boto3`).
- AWS Command Line Interface (CLI) installed and configured with your AWS credentials
  (run `aws configure` in your terminal). You need permissions to manage S3 and CloudFront
  (similar to the deployment script).
"""

import boto3
import logging
import time
import sys
from botocore.exceptions import ClientError, WaiterError
from typing import Optional, Tuple, Dict, List, Any

# --- Configuration ---

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Constants ---
POLLING_INTERVAL_SECONDS: int = 10 # How often to check deletion status
CLOUDFRONT_TIMEOUT_SECONDS: int = 600 # Max time to wait for CF disablement and deletion (10 mins)
S3_DELETE_TIMEOUT_SECONDS: int = 300 # Max time to wait for S3 objects deletion


# --- Helper Functions ---

def get_s3_bucket_region(bucket_name: str, s3_client: boto3.client) -> Optional[str]:
    """
    Tries to determine the AWS region of a given S3 bucket.

    Simple Explanation:
    AWS needs to know *where* your S3 folder (bucket) lives (which geographical 'Region').
    This function asks AWS, "Where is the bucket named '{bucket_name}' located?".
    It's important because the bucket's website address includes the region name.
    Special case: Buckets in the 'us-east-1' region might not report a specific location,
    so we assume 'us-east-1' if we don't get another answer.

    Args:
        bucket_name (str): The name of the S3 bucket.
        s3_client (boto3.client): An initialized S3 client.

    Returns:
        Optional[str]: The AWS region code (e.g., 'us-east-1', 'eu-west-2') or None if lookup fails.
    """
    try:
        response = s3_client.get_bucket_location(Bucket=bucket_name)
        # Note: A bucket in us-east-1 returns a None or empty LocationConstraint.
        region = response.get("LocationConstraint")
        if region is None:
            return "us-east-1" # Default to us-east-1 if no constraint
        return region
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            logger.error(f"Bucket '{bucket_name}' not found.")
        elif e.response['Error']['Code'] == 'AccessDenied':
            logger.error(f"Access denied when trying to get location for bucket '{bucket_name}'. Check permissions.")
        else:
            logger.error(f"Error getting bucket location for '{bucket_name}': {e}")
        return None

def find_cloudfront_for_s3_bucket(bucket_name: str, region: str, cf_client: boto3.client) -> Optional[Tuple[str, str]]:
    """
    Searches for a CloudFront distribution that uses the specified S3 bucket's
    website endpoint as an origin.

    Simple Explanation:
    This function is like a detective. It knows the S3 bucket's name and where it
    lives (Region). It builds the expected website address for that bucket (like
    'my-bucket.s3-website-us-east-1.amazonaws.com'). Then, it asks CloudFront for
    a list of all delivery networks (distributions) you have. For each one, it checks:
    "Is this distribution set up to get its files from our target S3 website address?".
    If it finds exactly one match, it reports the distribution's unique ID and a
    special code (ETag) needed to modify or delete it.

    Args:
        bucket_name (str): The name of the S3 bucket.
        region (str): The AWS region of the S3 bucket.
        cf_client (boto3.client): An initialized CloudFront client.

    Returns:
        Optional[Tuple[str, str]]: A tuple containing the Distribution ID and ETag
                                    if a unique match is found, otherwise None.
    """
    target_origin_domain: str = f"{bucket_name}.s3-website-{region}.amazonaws.com"
    logger.info(f"Searching for CloudFront distribution with origin: {target_origin_domain}")
    found_distribution: Optional[Tuple[str, str]] = None
    distribution_count: int = 0

    try:
        paginator = cf_client.get_paginator("list_distributions")
        for page in paginator.paginate():
            if "DistributionList" not in page or "Items" not in page["DistributionList"]:
                continue # Skip empty pages or lists

            for dist_summary in page["DistributionList"]["Items"]:
                dist_id: str = dist_summary["Id"]
                # Need to get the full config to check origins accurately
                try:
                    config_response = cf_client.get_distribution_config(Id=dist_id)
                    dist_config: Dict[str, Any] = config_response["DistributionConfig"]
                    etag: str = config_response["ETag"]

                    if "Origins" in dist_config and "Items" in dist_config["Origins"]:
                        for origin in dist_config["Origins"]["Items"]:
                            if origin.get("DomainName") == target_origin_domain:
                                logger.info(f"Found matching distribution: ID={dist_id}")
                                if distribution_count == 0:
                                    found_distribution = (dist_id, etag)
                                else:
                                    # Found more than one match - this is ambiguous
                                    logger.warning(f"Found multiple distributions using {target_origin_domain} as origin. Cannot proceed automatically.")
                                    logger.warning(f"  - Matched ID: {found_distribution[0]}")
                                    logger.warning(f"  - Matched ID: {dist_id}")
                                    return None # Abort if ambiguous
                                distribution_count += 1
                                break # Check next distribution once match found in this one
                except ClientError as e:
                     logger.warning(f"Could not get config for distribution {dist_id}. Skipping. Error: {e}")

        if distribution_count == 1:
            return found_distribution
        elif distribution_count == 0:
            logger.info("No CloudFront distribution found linked to this S3 website endpoint.")
            return None
        else:
             # Should have been caught earlier, but as a safeguard:
            logger.error("Logic error: Multiple distributions found but not handled.")
            return None

    except ClientError as e:
        logger.error(f"Error listing CloudFront distributions: {e}")
        return None


def confirm_deletion(bucket_name: str, distribution_id: Optional[str]) -> bool:
    """
    Asks the user for confirmation before proceeding with deletion.

    Simple Explanation:
    This is the important safety check! It tells you exactly what it plans
    to delete (the S3 bucket and the CloudFront distribution, if found).
    It then asks you to type 'yes' to confirm you really want to delete them.
    If you type anything else, it cancels the whole process.

    Args:
        bucket_name (str): The name of the S3 bucket to be deleted.
        distribution_id (Optional[str]): The ID of the CloudFront distribution to be deleted, if found.

    Returns:
        bool: True if the user confirms deletion, False otherwise.
    """
    print("\n" + "="*60)
    print("!!! WARNING: RESOURCE DELETION !!!")
    print("="*60)
    print(f"You are about to permanently delete the following AWS resources:")
    print(f"  - S3 Bucket:          {bucket_name}")
    if distribution_id:
        print(f"  - CloudFront Distro:  {distribution_id}")
    else:
        print("  - CloudFront Distro:  (No associated distribution found or selected)")
    print("\nTHIS ACTION CANNOT BE UNDONE.")
    print("="*60)

    try:
        confirmation = input("Type 'yes' to confirm deletion: ").strip().lower()
        if confirmation == "yes":
            logger.info("User confirmed deletion.")
            return True
        else:
            logger.warning("Deletion cancelled by user.")
            return False
    except EOFError: # Handle cases where input stream is closed unexpectedly
        logger.warning("Input stream closed. Deletion cancelled.")
        return False


# --- Deletion Functions ---

def delete_cloudfront_distribution(distribution_id: str, etag: str, cf_client: boto3.client) -> bool:
    """
    Disables, deletes, and waits for the deletion of a CloudFront distribution.

    Simple Explanation:
    This function handles the careful process of removing the CloudFront delivery network:
    1. Disable: It first tells CloudFront to stop serving files ('Enabled: False').
    2. Wait for Disable: It keeps checking every few seconds ("Is it disabled yet?")
       until CloudFront confirms the change is active everywhere ('Deployed' status)
       or until a timeout is reached.
    3. Delete: Once disabled, it tells AWS to delete the distribution permanently.
    4. Wait for Delete: It keeps checking every few seconds ("Is it gone yet?")
       until AWS confirms the distribution no longer exists or until a timeout is reached.

    Args:
        distribution_id (str): The ID of the distribution to delete.
        etag (str): The current ETag of the distribution (needed for initial check/update).
        cf_client (boto3.client): An initialized CloudFront client.

    Returns:
        bool: True if the distribution was successfully deleted, False otherwise.
    """
    logger.info(f"--- Step 1: Disabling CloudFront Distribution {distribution_id} ---")
    latest_etag = etag # Start with the ETag passed in

    try:
        # Get current config to check if already disabled and get latest ETag
        get_config_response = cf_client.get_distribution_config(Id=distribution_id)
        dist_config = get_config_response["DistributionConfig"]
        current_etag = get_config_response["ETag"] # Use the absolute latest ETag
        latest_etag = current_etag # Update latest_etag

        if not dist_config["Enabled"]:
            logger.info(f"Distribution {distribution_id} is already disabled.")
            # No need to update, proceed directly to deletion using the current_etag
        else:
            # Need to disable it
            dist_config["Enabled"] = False
            update_response = cf_client.update_distribution(
                DistributionConfig=dist_config, Id=distribution_id, IfMatch=current_etag
            )
            latest_etag = update_response["ETag"] # Get the new ETag after update request
            logger.info(f"Disable request sent (ETag: {latest_etag}). Waiting for distribution {distribution_id} to be fully disabled ('Deployed' status)...")

            # --- Custom Wait Loop for Disablement ---
            disable_start_time = time.time()
            while True:
                try:
                    get_dist_response = cf_client.get_distribution(Id=distribution_id)
                    current_status = get_dist_response['Distribution']['Status']
                    elapsed_time = time.time() - disable_start_time

                    if current_status == 'Deployed':
                        logger.info(f"✅ Distribution {distribution_id} successfully disabled (Status: {current_status}).")
                        break # Exit the disablement wait loop

                    if elapsed_time > CLOUDFRONT_TIMEOUT_SECONDS:
                        logger.error(f"Timeout waiting for CloudFront distribution {distribution_id} to disable (Status: {current_status}).")
                        return False

                    logger.info(f"⏳ Distribution {distribution_id} status is '{current_status}'. Waiting for disablement... ({int(elapsed_time)}s elapsed)")
                    time.sleep(POLLING_INTERVAL_SECONDS)

                except ClientError as e:
                    # Handle potential errors during polling
                    logger.error(f"Error checking disable status for {distribution_id}: {e}")
                    return False # Exit if status check fails

        # --- Step 2: Deleting CloudFront Distribution ---
        # Ensure we use the *very latest* ETag obtained either from get_distribution_config (if already disabled)
        # or from the update_distribution response.
        logger.info(f"--- Step 2: Deleting CloudFront Distribution {distribution_id} (using ETag: {latest_etag}) ---")
        cf_client.delete_distribution(Id=distribution_id, IfMatch=latest_etag)
        logger.info(f"Delete request sent for {distribution_id}. Waiting for deletion to complete...")

        # --- Step 3: Wait for Deletion (Custom Polling) ---
        delete_start_time = time.time()
        while True:
            try:
                cf_client.get_distribution(Id=distribution_id)
                # If the above call succeeds, it still exists
                elapsed_time = time.time() - delete_start_time
                if elapsed_time > CLOUDFRONT_TIMEOUT_SECONDS:
                    logger.error(f"Timeout waiting for CloudFront distribution {distribution_id} to be deleted.")
                    return False
                logger.info(f"⏳ Distribution {distribution_id} still exists. Waiting for deletion... ({int(elapsed_time)}s elapsed)")
                time.sleep(POLLING_INTERVAL_SECONDS)
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchDistribution":
                    logger.info(f"✅ CloudFront distribution {distribution_id} successfully deleted.")
                    return True
                else:
                    # Unexpected error during deletion polling
                    logger.error(f"Error checking deletion status for {distribution_id}: {e}")
                    return False

    except ClientError as e:
        # Handle errors during initial get/update or final delete calls
        if e.response["Error"]["Code"] == "NoSuchDistribution":
             logger.warning(f"CloudFront distribution {distribution_id} seems to be already deleted or does not exist.")
             return True # Treat as success if it's already gone
        elif e.response["Error"]["Code"] == "DistributionNotDisabled":
             # This might occur if delete is called before disablement is fully 'Deployed'
             logger.error(f"Failed to delete {distribution_id} because it reported as not disabled properly.")
             return False
        elif e.response["Error"]["Code"] == "IllegalUpdate":
             # Can occur if trying to update while another update is in progress
              logger.error(f"Failed to update {distribution_id}. Another update might be in progress. Error: {e}")
              return False
        elif e.response["Error"]["Code"] == "InvalidIfMatchVersion":
             logger.error(f"ETag mismatch when trying to modify/delete {distribution_id}. Might indicate a concurrent modification. Error: {e}")
             return False
        else:
            logger.error(f"An unexpected error occurred during CloudFront disable/delete process for {distribution_id}: {e}")
            return False

def empty_s3_bucket(bucket_name: str, s3_client: boto3.client) -> bool:
    """
    Deletes all objects (including all versions and delete markers) from an S3 bucket.

    Simple Explanation:
    Imagine the S3 bucket is a box full of files. We can't throw away the box until
    it's empty. This function systematically lists *everything* inside the bucket –
    all the current files, any old versions of files (if you had versioning turned on),
    and special markers for deleted files. It then tells S3 to delete all of these
    items in big batches (up to 1000 at a time) until the bucket is completely empty.
    It shows progress messages while it works.

    Args:
        bucket_name (str): The name of the bucket to empty.
        s3_client (boto3.client): An initialized S3 client.

    Returns:
        bool: True if the bucket was successfully emptied, False otherwise.
    """
    logger.info(f"--- Preparing to empty S3 bucket: {bucket_name} ---")
    objects_to_delete: List[Dict[str, str]] = []
    total_objects_found = 0
    start_time = time.time()

    try:
        # Check if versioning is enabled (best practice for cleanup)
        versioning = s3_client.get_bucket_versioning(Bucket=bucket_name)
        is_versioned = versioning.get("Status") == "Enabled"
        logger.info(f"Bucket versioning status: {'Enabled' if is_versioned else 'Disabled/Suspended'}")

        # Paginate through objects and versions/delete markers
        paginator = s3_client.get_paginator("list_object_versions")
        pages = paginator.paginate(Bucket=bucket_name)

        for page in pages:
            # Handle potential lack of keys in response
            versions = page.get("Versions", [])
            delete_markers = page.get("DeleteMarkers", [])

            if not versions and not delete_markers:
                 logger.debug(f"No objects, versions, or markers found in this page for {bucket_name}.")
                 continue

            if versions:
                for obj_version in versions:
                    objects_to_delete.append(
                        {"Key": obj_version["Key"], "VersionId": obj_version["VersionId"]}
                    )
                    total_objects_found += 1
            if delete_markers:
                for marker in delete_markers:
                    objects_to_delete.append(
                        {"Key": marker["Key"], "VersionId": marker["VersionId"]}
                    )
                    total_objects_found += 1

            logger.info(f"Found {total_objects_found} objects/versions/markers so far...")

            # Delete in batches of 1000 as we accumulate them
            while len(objects_to_delete) >= 1000:
                batch = objects_to_delete[:1000]
                objects_to_delete = objects_to_delete[1000:]
                logger.info(f"Deleting batch of {len(batch)} items...")
                delete_response = s3_client.delete_objects(
                    Bucket=bucket_name, Delete={"Objects": batch, "Quiet": True}
                )
                if "Errors" in delete_response and delete_response["Errors"]:
                    logger.error(f"Errors encountered deleting objects: {delete_response['Errors']}")
                    # Decide whether to stop or continue. Let's stop for safety.
                    return False
                if time.time() - start_time > S3_DELETE_TIMEOUT_SECONDS:
                     logger.error(f"Timeout ({S3_DELETE_TIMEOUT_SECONDS}s) reached while deleting objects from {bucket_name}.")
                     return False


        # Delete any remaining objects (less than 1000)
        if objects_to_delete:
            logger.info(f"Deleting final batch of {len(objects_to_delete)} items...")
            delete_response = s3_client.delete_objects(
                Bucket=bucket_name, Delete={"Objects": objects_to_delete, "Quiet": True}
            )
            if "Errors" in delete_response and delete_response["Errors"]:
                logger.error(f"Errors encountered deleting final batch of objects: {delete_response['Errors']}")
                return False

        logger.info(f"Successfully deleted {total_objects_found} items from bucket {bucket_name}.")
        return True

    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
             # If bucket is already gone, consider it emptied successfully in this context
             logger.warning(f"Bucket {bucket_name} not found while trying to empty it. Assuming already deleted/emptied.")
             return True
        else:
            logger.error(f"Error emptying bucket {bucket_name}: {e}")
            return False

def delete_s3_bucket(bucket_name: str, s3_client: boto3.client) -> bool:
    """
    Deletes an S3 bucket after confirming it's empty.

    Simple Explanation:
    Once the S3 bucket (box) is confirmed to be empty, this function tells AWS
    to delete the bucket itself. It then waits using an official 'Waiter' until
    AWS confirms the bucket no longer exists.

    Args:
        bucket_name (str): The name of the bucket to delete.
        s3_client (boto3.client): An initialized S3 client.

    Returns:
        bool: True if the bucket was successfully deleted, False otherwise.
    """
    logger.info(f"--- Deleting S3 bucket: {bucket_name} ---")
    try:
        s3_client.delete_bucket(Bucket=bucket_name)
        logger.info(f"Delete request sent for bucket {bucket_name}. Waiting for confirmation...")

        # Wait for the bucket to not exist
        waiter = s3_client.get_waiter("bucket_not_exists")
        waiter.wait(
            Bucket=bucket_name,
            WaiterConfig={"Delay": 15, "MaxAttempts": 20} # Wait up to 5 mins
        )
        logger.info(f"S3 bucket {bucket_name} successfully deleted.")
        return True
    except WaiterError as e:
        logger.error(f"Error or timeout waiting for bucket {bucket_name} deletion: {e}")
        return False
    except ClientError as e:
         if e.response['Error']['Code'] == 'NoSuchBucket':
             logger.warning(f"Bucket {bucket_name} seems to be already deleted.")
             return True # Already gone, treat as success
         else:
            logger.error(f"Error deleting bucket {bucket_name}: {e}")
            # Common error: BucketNotEmpty - should be caught by empty_s3_bucket, but log if occurs
            if e.response['Error']['Code'] == 'BucketNotEmpty':
                 logger.error("Deletion failed because the bucket is not empty. Emptying step might have failed.")
            return False

# --- Main Orchestration ---

def main() -> None:
    """
    Main function to orchestrate the cleanup process.

    Simple Explanation:
    This is the main conductor for the cleanup script. It runs the steps in order:
    1. Initializes connections to AWS (S3 and CloudFront).
    2. Asks you which S3 bucket to target.
    3. Tries to figure out the bucket's region.
    4. Searches for a linked CloudFront distribution.
    5. Asks for your final confirmation.
    6. If confirmed, it proceeds with the careful deletion steps:
       - Delete CloudFront (disable, wait, delete, wait).
       - Empty S3 Bucket (delete all objects/versions).
       - Delete S3 Bucket (wait until gone).
    7. Reports the final outcome. It stops if any critical step fails or if you cancel.
    """
    logger.info("===============================================")
    logger.info(" Starting AWS S3 & CloudFront Resource Cleanup ")
    logger.info("===============================================")

    try:
        s3_client: boto3.client = boto3.client("s3")
        cf_client: boto3.client = boto3.client("cloudfront")
    except Exception as e:
         logger.error(f"Failed to initialize AWS clients. Check credentials and boto3 installation. Error: {e}")
         sys.exit(1)


    # 1. Get Target Bucket Name
    bucket_name: Optional[str] = input("Enter the name of the S3 bucket to delete: ").strip()
    if not bucket_name:
        logger.error("No bucket name provided. Exiting.")
        sys.exit(1)

    logger.info(f"Target S3 bucket for deletion: {bucket_name}")

    # 2. Determine Bucket Region
    region = get_s3_bucket_region(bucket_name, s3_client)
    if not region:
        region = input(f"Could not determine region for bucket '{bucket_name}'. Please enter the region manually: ").strip()
        if not region:
            logger.error(f"Region not provided. Cannot reliably find CloudFront distribution. Exiting.")
            sys.exit(1)
    logger.info(f"Determined region for bucket '{bucket_name}' is: {region}")

    # 3. Find Associated CloudFront Distribution
    cf_info: Optional[Tuple[str, str]] = find_cloudfront_for_s3_bucket(bucket_name, region, cf_client)
    distribution_id: Optional[str] = cf_info[0] if cf_info else None
    distribution_etag: Optional[str] = cf_info[1] if cf_info else None

    # 4. Confirm Deletion
    if not confirm_deletion(bucket_name, distribution_id):
        sys.exit(0) # Exit gracefully if user cancels

    # --- Start Deletion Process ---
    cloudfront_deleted_successfully: bool = False
    bucket_emptied_successfully: bool = False
    bucket_deleted_successfully: bool = False

    # 5. Delete CloudFront (if found)
    if distribution_id and distribution_etag:
        cloudfront_deleted_successfully = delete_cloudfront_distribution(
            distribution_id, distribution_etag, cf_client
        )
        if not cloudfront_deleted_successfully:
            logger.error(f"CloudFront distribution {distribution_id} deletion failed. Stopping cleanup.")
            # We stop because the S3 bucket might still be locked by the enabled/partially-deleted CF distro
            sys.exit(1)
    else:
        logger.info("Skipping CloudFront deletion (none found or identified).")
        cloudfront_deleted_successfully = True # Consider it successful if there was nothing to delete

    # 6. Empty S3 Bucket (only if CF deletion succeeded or wasn't needed)
    if cloudfront_deleted_successfully:
        bucket_emptied_successfully = empty_s3_bucket(bucket_name, s3_client)
        if not bucket_emptied_successfully:
             logger.error(f"Failed to empty S3 bucket {bucket_name}. Cannot proceed with bucket deletion.")
             sys.exit(1)

    # 7. Delete S3 Bucket (only if emptied successfully)
    if bucket_emptied_successfully:
        bucket_deleted_successfully = delete_s3_bucket(bucket_name, s3_client)

    # --- Final Summary ---
    print("\n" + "=" * 60)
    print("          CLEANUP SUMMARY")
    print("=" * 60)
    if distribution_id:
         print(f" CloudFront ({distribution_id}): {'DELETED' if cloudfront_deleted_successfully else 'FAILED'}")
    else:
         print(f" CloudFront:            {'N/A (None Found)'}")

    print(f" S3 Bucket Objects ({bucket_name}): {'DELETED' if bucket_emptied_successfully else 'FAILED'}")
    print(f" S3 Bucket ({bucket_name}): {'DELETED' if bucket_deleted_successfully else 'FAILED'}")
    print("=" * 60)

    if cloudfront_deleted_successfully and bucket_emptied_successfully and bucket_deleted_successfully:
        logger.info("Cleanup process completed successfully.")
    else:
        logger.error("Cleanup process finished with errors. Please review logs.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Aborted by user. Exiting.")