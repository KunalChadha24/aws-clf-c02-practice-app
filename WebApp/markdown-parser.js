class MarkdownParser {
    constructor() {
        this.questions = [];
    }

    async parseMarkdownFile(filePath) {
        try {
            const response = await fetch(filePath);
            if (!response.ok) {
                throw new Error(`Failed to fetch markdown file: ${response.status} ${response.statusText}`);
            }
            
            const markdown = await response.text();
            return this.parseQuestions(markdown);
        } catch (error) {
            console.error('Error parsing markdown file:', error);
            return [];
        }
    }

    parseQuestions(markdown) {
        // Reset questions array
        this.questions = [];
        
        // Split the markdown by question numbers (1., 2., etc.)
        const questionRegex = /(\d+)\.\s+(.*?)(?=\n\s*\d+\.\s+|\n*$)/gs;
        const matches = [...markdown.matchAll(questionRegex)];
        
        matches.forEach(match => {
            const questionNumber = parseInt(match[1]);
            const questionContent = match[2].trim();
            
            // Parse the question text and options
            const questionData = this.parseQuestionContent(questionContent, questionNumber);
            if (questionData) {
                this.questions.push(questionData);
            }
        });
        
        return this.questions;
    }

    parseQuestionContent(content, id) {
        // Extract question text (everything before the first option)
        const questionTextMatch = content.match(/(.*?)(?=\s*-\s*[A-Z]\.)/s);
        if (!questionTextMatch) return null;
        
        const questionText = questionTextMatch[1].trim();
        
        // Extract options
        const optionsRegex = /-\s*([A-Z])\.\s*(.*?)(?=\s*-\s*[A-Z]\.|\s*<details|\s*$)/gs;
        const optionsMatches = [...content.matchAll(optionsRegex)];
        
        const options = optionsMatches.map(match => ({
            id: match[1],
            text: match[2].trim()
        }));
        
        // Extract correct answers - updated regex to match both formats:
        // 1. Correct answer: X
        // 2. Correct Answer: X
        // 3. Correct answer(s): X, Y, Z
        const answerRegex = /<details.*?>\s*Correct [aA]nswer(?:\(s\))?:?\s*([A-Za-z,\s]+)(?:\s*(?:Explanation:.*?)?)?<\/details>/s;
        const answerMatch = content.match(answerRegex);
        
        let correctAnswers = [];
        if (answerMatch && answerMatch[1]) {
            // Process the answer text to extract letter options
            const answerText = answerMatch[1].trim();
            
            // Check if it's a comma-separated list like "A, B, C"
            if (answerText.includes(',')) {
                correctAnswers = answerText.split(',').map(a => a.trim().charAt(0));
            } 
            // Check if it contains the word "and" like "A and B"
            else if (answerText.includes(' and ')) {
                correctAnswers = answerText.split(' and ').map(a => a.trim().charAt(0));
            }
            // Check if it's a format like "Correct answer: D"
            else if (answerText.match(/^[A-Z]$/)) {
                correctAnswers = [answerText];
            }
            // Check if it's a format like "D" or contains a letter like "Correct answer: D"
            else {
                // Extract any capital letters that might be the answer
                const letterMatches = answerText.match(/[A-Z]/g);
                if (letterMatches) {
                    correctAnswers = letterMatches;
                }
            }
        }
        
        // Extract explanation if available
        let explanation = "";
        const explanationRegex = /Explanation:([^<]*?)(?:<\/details>|$)/s;
        const explanationMatch = content.match(explanationRegex);
        
        if (explanationMatch && explanationMatch[1]) {
            explanation = explanationMatch[1].trim();
        }
        
        return {
            id,
            text: questionText,
            options,
            correctAnswers,
            explanation
        };
    }
}
