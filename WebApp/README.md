# AWS Certified Cloud Practitioner Practice Exam Application

An interactive web application for practicing AWS Certified Cloud Practitioner (CLF-C02) exam questions.

![AWS Certified Cloud Practitioner](https://d1.awsstatic.com/training-and-certification/certification-badges/AWS-Certified-Cloud-Practitioner_badge.634f8a21af2e0e956ed8905a72366146ba22b74c.png)

## Features

- 23 practice exams with real-world style questions
- Timed exam simulation (90 minutes)
- Support for both single and multiple-choice questions
- Review section highlighting correct answers
- Responsive design that works on all devices
- No backend required - runs entirely in the browser

## Getting Started

### Local Development

1. Clone this repository or download the files
2. Open `index.html` in your web browser
3. Select a practice exam from the dropdown menu
4. Start the exam and test your AWS knowledge!

You can also use a local server to serve the files:

```bash
# Using Python's built-in HTTP server
python -m http.server 8080
```

Then navigate to `http://localhost:8080` in your browser.

## File Structure

- `index.html` - Main HTML file
- `styles.css` - CSS styling
- `app.js` - Main application logic
- `markdown-parser.js` - Parser for loading questions from markdown files
- `markdown-files.json` - Configuration file for available practice exams
- `exam-template/` - Directory containing markdown files with exam questions

## Exam Content

The application loads exam questions from markdown files in the `exam-template` directory. Each file contains a set of practice questions with answers and explanations.

## Adding More Practice Exams

To add more practice exams:

1. Create a new markdown file in the `exam-template` directory following the existing format
2. Update the `markdown-files.json` file to include your new exam
3. Reload the application to see your new exam in the dropdown menu

## License

This project is open source and available for personal use.

## Acknowledgements

- Exam questions sourced from [kananinirav/AWS-Certified-Cloud-Practitioner-Notes](https://github.com/kananinirav/AWS-Certified-Cloud-Practitioner-Notes).
- Built with Vanilla JavaScript, HTML, and CSS.
