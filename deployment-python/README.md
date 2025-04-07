# AWS Certified Cloud Practitioner (CLF-C02) Practice Exam WebApp Deployment on AWS

This project provides Python scripts to automate the deployment and cleanup of a static website using AWS S3 for hosting and AWS CloudFront for global content delivery (CDN).

-   **`deploy.py`**: Creates an S3 bucket, configures it for static website hosting, uploads your website files, and sets up a CloudFront distribution pointing to the S3 website endpoint for low-latency access and HTTPS.
-   **`cleanup.py`**: Safely deletes the CloudFront distribution and the S3 bucket (including all its contents) created by the deployment script to avoid ongoing AWS charges.

## Overview

### How it Works

1.  **S3 Static Website Hosting:** We use AWS S3 (Simple Storage Service) like a specialized web server. We create a "bucket" (like a folder), upload your website's HTML, CSS, JavaScript, and image files into it, and configure the bucket to serve these files publicly over the internet via a unique S3 website URL.
2.  **CloudFront CDN:** To make your website load quickly for users anywhere in the world and serve it over secure HTTPS, we use AWS CloudFront. CloudFront acts as a Content Delivery Network (CDN). It caches copies of your website files in numerous "Edge Locations" globally. When a user visits your site, they are served content from the nearest edge location, significantly reducing latency. CloudFront also handles the redirection from HTTP to HTTPS.

### Benefits

-   **Cost-Effective:** S3 and CloudFront offer a very low-cost way to host static websites, often falling within the AWS Free Tier for low-traffic sites.
-   **Scalable & Reliable:** AWS services handle scaling automatically, ensuring your site remains available even under high traffic.
-   **Global Performance:** CloudFront ensures fast loading times for users worldwide.
-   **Automation:** These scripts automate the setup and teardown process, reducing manual effort and potential errors.

## Prerequisites

Before you begin, ensure you have the following installed and configured:

1.  **Python:**
    -   Python 3.8 or newer is recommended.
    -   Verify your installation: `python --version` or `python3 --version`.
    -   Download from [python.org](https://www.python.org/).

2.  **AWS Account:**
    -   You need an active AWS account. Sign up at [aws.amazon.com](https://aws.amazon.com/).

3.  **AWS Command Line Interface (CLI):**
    -   The AWS CLI is used to easily configure your AWS credentials.
    -   Installation Instructions ([Official Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)):
        -   **Windows:** Download and run the MSI installer from the [AWS CLIv2 download page](https://aws.amazon.com/cli/).
        -   **macOS:** Download and run the PKG installer from the [AWS CLIv2 download page](https://aws.amazon.com/cli/), or use Homebrew: `brew install awscli`.
        -   **Linux:** Use the bundled installer (check official guide for detailed steps using `curl` and `unzip`). Alternatively, if `pip` is available system-wide (use with caution or in a dedicated environment): `pip install awscli`.
    -   Verify installation: `aws --version`.

4.  **AWS Credentials Configuration:**
    -   You need AWS Access Keys (Access Key ID and Secret Access Key) associated with an IAM user that has sufficient permissions.
    -   **Permissions:** For these scripts, the IAM user needs permissions to manage S3 (create/delete buckets, put/delete objects, configure hosting/policy) and CloudFront (create/update/delete distributions). For simplicity, you could attach the `AmazonS3FullAccess` and `CloudFrontFullAccess` managed policies, but it's **highly recommended** to create a custom policy with least privilege for production use.
    -   Run the configure command:
        ```bash
        aws configure
        ```
    -   Enter the requested information:
        ```
        AWS Access Key ID [None]: YOUR_ACCESS_KEY_ID
        AWS Secret Access Key [None]: YOUR_SECRET_ACCESS_KEY
        Default region name [None]: us-east-1  # Or your preferred region, e.g., eu-west-1
        Default output format [None]: json     # Or yaml/text
        ```
    -   **Security:** Never commit your credentials directly into code or share your Secret Access Key. Use the `aws configure` method or other secure AWS credential management practices.

## Setup & Installation

1.  **Clone the Repository (if applicable):**
    ```bash
    git clone <your-repository-url>
    cd <repository-directory>
    ```

2.  **Create and Activate a Virtual Environment:**
    -   Using a virtual environment is highly recommended to isolate project dependencies.
    -   **Windows (Command Prompt/PowerShell):**
        ```bash
        # Create the virtual environment (named 'venv')
        python -m venv venv
        # Activate it
        .\venv\Scripts\activate
        ```
    -   **macOS/Linux (Bash/Zsh):**
        ```bash
        # Create the virtual environment (named 'venv')
        python3 -m venv venv
        # Activate it
        source venv/bin/activate
        ```
    -   You should see `(venv)` prefixed to your terminal prompt when active.

3.  **Install Dependencies:**
    -   Create a file named `requirements.txt` in your project directory with the following content:
        ```txt
        # requirements.txt
        boto3>=1.20.0 # AWS SDK for Python
        ```
    -   Install the required library using pip:
        ```bash
        pip install -r requirements.txt
        ```

## Running the Deployment Script (`deploy.py`)

This script sets up your S3 bucket, uploads files, and creates the CloudFront distribution.

1.  **Place your Website Files:** Ensure your static website files (e.g., `index.html`, `error.html`, CSS folders, JS folders, image folders) are located in the directory specified by the `SOURCE_DIR` variable within the `deploy.py` script (default is `../WebApp`, the parent directory).
2.  **Run the Script:**
    ```bash
    python deploy.py
    ```
3.  **Prompts:**
    -   The script will prompt you to enter an S3 bucket name or accept the generated default name. Bucket names must be globally unique.
4.  **Output:**
    -   The script logs its progress to the console.
    -   Upon successful completion, it prints a summary including:
        -   The S3 Bucket Name.
        -   The S3 Static Website URL (accessible via HTTP, useful for testing but use CloudFront URL primarily).
        -   The CloudFront Distribution ID.
        -   The CloudFront Domain Name/URL (e.g., `https://d123abcd.cloudfront.net`). This is the primary URL you should use to access your website.
    -   **Note:** CloudFront distributions take **15-20 minutes** to deploy globally after the script finishes. Your CloudFront URL might not work immediately.

## Running the Cleanup Script (`cleanup.py`)

This script deletes the CloudFront distribution and S3 bucket to stop incurring charges.

1.  **Run the Script:**
    ```bash
    python cleanup.py
    ```
2.  **Prompts:**
    -   It will ask for the **exact name** of the S3 bucket you wish to delete.
    -   It will then attempt to find the associated CloudFront distribution automatically.
    -   **CRITICAL:** It will show you the resources it identified (bucket and possibly distribution) and ask for explicit confirmation (`yes`) before deleting anything. **This action is irreversible.**
3.  **Output:**
    -   The script logs its progress, including status updates during the disabling and deletion phases of CloudFront and the emptying and deletion of the S3 bucket.
    -   It prints a final summary indicating whether each resource was successfully deleted or if any errors occurred.

## Configuration / Customization

You can modify the following constants near the top of `deploy.py` to suit your needs:

-   `REGION` (string): The AWS region where the S3 bucket will be created (e.g., `"us-east-1"`, `"eu-west-2"`). Ensure this matches your `aws configure` default region or your intended deployment region.
-   `SOURCE_DIR` (string): The path (relative to `deploy.py`) to the directory containing your website files (HTML, CSS, JS, images, etc.). Default is `"../WebApp"`.
-   `EXCLUDE_EXTENSIONS` (list of strings): File extensions that will *not* be uploaded to the S3 bucket (e.g., `[".py", ".ps1", ".git"]`).
-   `EXCLUDE_DIRS` (list of strings): Directory names that will *not* be uploaded (e.g., `[".git", "__pycache__"]`).

You can modify the following constants near the top of `cleanup.py`:

-   `POLLING_INTERVAL_SECONDS` (integer): How often (in seconds) the script checks the status during CloudFront disable/delete and S3 delete waits.
-   `CLOUDFRONT_DISABLE_TIMEOUT_SECONDS` / `CLOUDFRONT_DELETE_TIMEOUT_SECONDS` / `S3_DELETE_TIMEOUT_SECONDS` (integers): Maximum time (in seconds) the script will wait for each respective step before timing out.
