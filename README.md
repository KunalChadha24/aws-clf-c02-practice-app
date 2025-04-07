# AWS Certified Cloud Practitioner (CLF-C02) Practice Exam Application

This repository contains an interactive web application for practicing AWS Certified Cloud Practitioner (CLF-C02) exam questions, along with deployment options for hosting it on AWS using either Python (boto3) or Terraform.

![AWS Certified Cloud Practitioner](https://d1.awsstatic.com/training-and-certification/certification-badges/AWS-Certified-Cloud-Practitioner_badge.634f8a21af2e0e956ed8905a72366146ba22b74c.png)

## Directory Structure

This project is organized into three main directories, each with its own README file for detailed information:

### 1. [`WebApp/`](./WebApp/README.md)

Contains the core web application files for the AWS CLF-C02 practice exam:

- Interactive exam interface with 23 practice exams
- Support for single and multiple-choice questions
- Timed exam simulation (90 minutes)
- Review section with correct answer highlighting
- Responsive design for all devices
- No backend required - runs entirely in the browser

The application loads questions from markdown files and provides an exam experience similar to the actual AWS certification exam.

### 2. [`deployment-python/`](./deployment-python/README.md)

Contains Python scripts using boto3 to deploy the web application to AWS:

- `deploy.py` - Automates the creation of an S3 bucket for static website hosting and sets up a CloudFront distribution for global content delivery
- `cleanup.py` - Safely removes all AWS resources created during deployment
- Detailed README with step-by-step instructions for AWS deployment

This approach is ideal for users who prefer Python and want a programmatic way to manage AWS resources.

### 3. [`deployment-terraform/`](./deployment-terraform/README.md)

Contains Terraform configuration files to deploy the web application to AWS using Infrastructure as Code:

- Defines AWS resources (S3, CloudFront) in declarative configuration files
- Provides a consistent and repeatable deployment process
- Includes variables for customization and outputs for resource information
- Supports easy cleanup with `terraform destroy`

This approach is ideal for users familiar with Terraform and infrastructure as code practices.

## Who Can Benefit From This Project

This project is designed for:

1. **AWS Certification Candidates** - Individuals preparing for the AWS Certified Cloud Practitioner (CLF-C02) exam who want realistic practice questions in an exam-like environment.

2. **Cloud Computing Students** - Students learning about AWS services and cloud concepts who want to test their knowledge.

3. **IT Professionals** - Professionals transitioning to cloud roles who need to validate their understanding of AWS fundamentals.

4. **DevOps/Cloud Engineers** - Engineers who want to practice both AWS certification content and learn about different deployment approaches (Python vs. Terraform).

5. **Educators** - Teachers and trainers who need a platform to help students prepare for AWS certification.

## Deployment Options

This project provides two different approaches to deploy the application to AWS:

### Python Deployment (boto3)

The `deployment-python/` directory contains Python scripts that use the AWS SDK (boto3) to:

1. Create an S3 bucket configured for static website hosting
2. Upload the web application files
3. Set up a CloudFront distribution for global content delivery with HTTPS

This approach is ideal for Python developers and those who prefer a script-based deployment process.

See the [deployment-python README](./deployment-python/README.md) for detailed instructions.

### Terraform Deployment (IaC)

The `deployment-terraform/` directory contains Terraform configuration files that:

1. Define all required AWS resources (S3, CloudFront) as code
2. Provide a declarative approach to infrastructure management
3. Support easy updates and teardown of the infrastructure

This approach is ideal for those familiar with Infrastructure as Code and Terraform specifically.

See the [deployment-terraform README](./deployment-terraform/README.md) for detailed instructions.

## Getting Started

1. Clone or download this repository
2. Explore the web application locally by opening `WebApp/index.html` in your browser
3. Choose your preferred deployment method:
   - For Python deployment: Follow the instructions in the [deployment-python README](./deployment-python/README.md)
   - For Terraform deployment: Follow the instructions in the [deployment-terraform README](./deployment-terraform/README.md)

## License

This project is open source and available for personal use.

## Support

If you encounter any issues or have questions, please feel free to reach out:

-   **LinkedIn:** [Kunal Chadha](https://www.linkedin.com/in/kunal-chadha-8034161a8/)
-   **GitHub Issues:** Please file an issue in the repository.
