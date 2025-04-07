document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const introScreen = document.getElementById('intro-screen');
    const examContainer = document.getElementById('exam-container');
    const resultsScreen = document.getElementById('results-screen');
    const questionContainer = document.getElementById('question-container');
    const startBtn = document.getElementById('start-exam');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const submitBtn = document.getElementById('submit-btn');
    const restartBtn = document.getElementById('restart-btn');
    const timeElement = document.getElementById('time');
    const currentQuestionElement = document.getElementById('current-question');
    const totalQuestionsElement = document.getElementById('total-questions');
    const scoreElement = document.getElementById('score');
    const totalElement = document.getElementById('total');
    const percentageElement = document.getElementById('percentage');
    const reviewQuestionsElement = document.getElementById('review-questions');
    const markdownFileSelect = document.getElementById('markdown-file');

    // Exam state
    let currentQuestionIndex = 0;
    let userAnswers = {};
    let examStarted = false;
    let examTime = 90 * 60; // 90 minutes in seconds
    let timerInterval;
    let questions = [];
    
    // Wait for questions to be loaded before initializing
    let questionsLoaded = false;
    
    // Load markdown files from JSON
    async function loadMarkdownFiles() {
        try {
            const response = await fetch('markdown-files.json');
            if (!response.ok) {
                throw new Error(`Failed to fetch markdown files: ${response.status} ${response.statusText}`);
            }
            
            const markdownFiles = await response.json();
            
            // Clear existing options
            markdownFileSelect.innerHTML = '';
            
            // Add options from JSON
            markdownFiles.forEach(file => {
                const option = document.createElement('option');
                option.value = file.filename;
                option.textContent = file.title;
                markdownFileSelect.appendChild(option);
            });
            
            // Set initial value
            const savedFile = localStorage.getItem('selectedMarkdownFile') || markdownFiles[0].filename;
            markdownFileSelect.value = savedFile;
            loadQuestionsFromFile(savedFile);
        } catch (error) {
            console.error('Error loading markdown files:', error);
            // Fallback to readme.md if there's an error
            loadQuestionsFromFile('readme.md');
        }
    }
    
    // Load questions from the selected markdown file
    async function loadQuestionsFromFile(filePath) {
        questionsLoaded = false;
        const parser = new MarkdownParser();
        questions = await parser.parseMarkdownFile(filePath);
        questionsLoaded = true;
        initExam();
        return questions;
    }
    
    // Handle file selection change
    markdownFileSelect.addEventListener('change', (e) => {
        const selectedFile = e.target.value;
        localStorage.setItem('selectedMarkdownFile', selectedFile);
        loadQuestionsFromFile(selectedFile);
    });
    
    // Load markdown files from JSON
    loadMarkdownFiles();

    // Initialize the exam
    function initExam() {
        // Only initialize if questions are loaded
        if (!questionsLoaded || !questions || questions.length === 0) {
            return;
        }
        
        // Shuffle questions for randomization
        shuffleQuestions();
        
        // Set total questions
        totalQuestionsElement.textContent = questions.length;
        
        // Reset user answers
        userAnswers = {};
        
        // Reset current question index
        currentQuestionIndex = 0;
        
        // Update navigation buttons
        updateNavButtons();
    }

    // Shuffle the questions array
    function shuffleQuestions() {
        for (let i = questions.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [questions[i], questions[j]] = [questions[j], questions[i]];
        }
        
        // Re-assign IDs after shuffling
        questions.forEach((question, index) => {
            question.id = index + 1;
        });
    }

    // Start the exam
    function startExam() {
        if (!questionsLoaded || !questions || questions.length === 0) {
            alert("Questions are still loading. Please wait a moment.");
            return;
        }
        
        examStarted = true;
        introScreen.style.display = 'none';
        examContainer.style.display = 'block';
        
        // Start the timer
        startTimer();
        
        // Load the first question
        loadQuestion(currentQuestionIndex);
    }

    // Load a question
    function loadQuestion(index) {
        if (!questionsLoaded || questions.length === 0) {
            return;
        }
        
        const question = questions[index];
        currentQuestionIndex = index;
        
        // Update current question number
        currentQuestionElement.textContent = index + 1;
        totalQuestionsElement.textContent = questions.length;
        
        // Clear previous question
        questionContainer.innerHTML = '';
        
        // Create question header
        const questionHeader = document.createElement('div');
        questionHeader.classList.add('question-header');
        
        // Check if the question text contains indicators for multiple answers
        const isMultipleChoice = question.text.match(/choose\s+(\w+)/i) || 
                                question.text.match(/select\s+(\w+)/i) ||
                                question.text.includes("TWO") ||
                                question.text.includes("THREE") ||
                                question.text.includes("multiple") ||
                                question.correctAnswers.length > 1;
        
        // Add multiple choice indicator if applicable
        if (isMultipleChoice) {
            questionHeader.innerHTML = `<h3>Question ${index + 1}</h3><p class="multiple-choice-indicator">(Select all that apply)</p>`;
        } else {
            questionHeader.innerHTML = `<h3>Question ${index + 1}</h3>`;
        }
        
        questionContainer.appendChild(questionHeader);
        
        // Create question text
        const questionText = document.createElement('div');
        questionText.classList.add('question-text');
        questionText.textContent = question.text;
        questionContainer.appendChild(questionText);
        
        // Create options
        const optionsList = document.createElement('ul');
        optionsList.classList.add('options');
        
        question.options.forEach(option => {
            const optionItem = document.createElement('li');
            optionItem.classList.add('option');
            optionItem.dataset.id = option.id;
            
            // Check if this option is selected by the user
            if (userAnswers[question.id] && userAnswers[question.id].includes(option.id)) {
                optionItem.classList.add('selected');
            }
            
            optionItem.innerHTML = `<span class="option-id">${option.id}.</span> <span class="option-text">${option.text}</span>`;
            
            // Add click event
            optionItem.addEventListener('click', () => {
                toggleOption(optionItem, question);
            });
            
            optionsList.appendChild(optionItem);
        });
        
        questionContainer.appendChild(optionsList);
        
        // Update navigation buttons
        updateNavButtons();
    }

    // Toggle option selection
    function toggleOption(optionElement, question) {
        const optionId = optionElement.dataset.id;
        
        // Initialize user answers for this question if not exists
        if (!userAnswers[question.id]) {
            userAnswers[question.id] = [];
        }
        
        // Check if this is a multi-answer question
        const isMultiAnswer = question.text.match(/choose\s+(\w+)/i) || 
                             question.text.match(/select\s+(\w+)/i) ||
                             question.text.includes("TWO") ||
                             question.text.includes("THREE") ||
                             question.text.includes("multiple") ||
                             question.correctAnswers.length > 1;
        
        if (isMultiAnswer) {
            // For multi-answer questions, toggle the selection
            if (userAnswers[question.id].includes(optionId)) {
                // Remove the option if already selected
                userAnswers[question.id] = userAnswers[question.id].filter(id => id !== optionId);
                optionElement.classList.remove('selected');
            } else {
                // Add the option if not selected
                userAnswers[question.id].push(optionId);
                optionElement.classList.add('selected');
            }
        } else {
            // For single-answer questions, clear previous selection
            const options = questionContainer.querySelectorAll('.option');
            options.forEach(option => {
                option.classList.remove('selected');
            });
            
            // Select the clicked option
            userAnswers[question.id] = [optionId];
            optionElement.classList.add('selected');
        }
    }

    // Update navigation buttons
    function updateNavButtons() {
        // Disable prev button if on first question
        prevBtn.disabled = currentQuestionIndex === 0;
        
        // Show submit button on last question, otherwise show next button
        if (currentQuestionIndex === questions.length - 1) {
            nextBtn.style.display = 'none';
            submitBtn.style.display = 'block';
        } else {
            nextBtn.style.display = 'block';
            submitBtn.style.display = 'none';
        }
    }

    // Start the timer
    function startTimer() {
        timerInterval = setInterval(() => {
            examTime--;
            
            if (examTime <= 0) {
                // Time's up, submit the exam
                clearInterval(timerInterval);
                submitExam();
            } else {
                // Update timer display
                const minutes = Math.floor(examTime / 60);
                const seconds = examTime % 60;
                timeElement.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            }
        }, 1000);
    }

    // Submit the exam
    function submitExam() {
        // Stop the timer
        clearInterval(timerInterval);
        
        // Calculate score
        const { score, total } = calculateScore();
        
        // Update results screen
        scoreElement.textContent = score;
        totalElement.textContent = total;
        
        // Calculate percentage
        const percentage = Math.round((score / total) * 100);
        percentageElement.textContent = `${percentage}%`;
        
        // Generate review content
        generateReviewContent();
        
        // Show results screen
        examContainer.style.display = 'none';
        resultsScreen.style.display = 'block';
    }

    // Calculate the score
    function calculateScore() {
        let score = 0;
        const total = questions.length;
        
        questions.forEach(question => {
            const userAnswer = userAnswers[question.id] || [];
            const correctAnswers = question.correctAnswers;
            
            // Check if arrays are equal (ignoring order)
            if (arraysEqual(userAnswer.sort(), correctAnswers.sort())) {
                score++;
            }
        });
        
        return { score, total };
    }

    // Check if two arrays are equal
    function arraysEqual(arr1, arr2) {
        if (arr1.length !== arr2.length) return false;
        
        for (let i = 0; i < arr1.length; i++) {
            if (arr1[i] !== arr2[i]) return false;
        }
        
        return true;
    }

    // Generate review content
    function generateReviewContent() {
        reviewQuestionsElement.innerHTML = '';
        
        questions.forEach(question => {
            const userAnswer = userAnswers[question.id] || [];
            const correctAnswers = question.correctAnswers;
            const isCorrect = arraysEqual(userAnswer.sort(), correctAnswers.sort());
            
            const reviewItem = document.createElement('div');
            reviewItem.classList.add('review-question');
            
            // Question header with result
            const header = document.createElement('div');
            header.classList.add('review-header');
            header.innerHTML = `
                <strong>Question ${question.id}:</strong> 
                <span class="${isCorrect ? 'correct' : 'incorrect'}">
                    ${isCorrect ? '✓ Correct' : '✗ Incorrect'}
                </span>
            `;
            reviewItem.appendChild(header);
            
            // Question text
            const questionText = document.createElement('div');
            questionText.classList.add('review-question-text');
            questionText.textContent = question.text;
            reviewItem.appendChild(questionText);
            
            // Options
            const optionsList = document.createElement('ul');
            optionsList.classList.add('review-options');
            
            question.options.forEach(option => {
                const optionItem = document.createElement('li');
                
                // Determine option class
                if (correctAnswers.includes(option.id) && userAnswer.includes(option.id)) {
                    // Correct answer and user selected it
                    optionItem.classList.add('correct');
                    optionItem.innerHTML = `<strong>${option.id}.</strong> ${option.text} ✓`;
                } else if (correctAnswers.includes(option.id) && !userAnswer.includes(option.id)) {
                    // Correct answer but user didn't select it
                    optionItem.classList.add('missed');
                    optionItem.innerHTML = `<strong>${option.id}.</strong> ${option.text}`;
                } else if (!correctAnswers.includes(option.id) && userAnswer.includes(option.id)) {
                    // Incorrect answer but user selected it
                    optionItem.classList.add('incorrect');
                    optionItem.innerHTML = `<strong>${option.id}.</strong> ${option.text}`;
                } else {
                    // Regular option
                    optionItem.innerHTML = `<strong>${option.id}.</strong> ${option.text}`;
                }
                
                optionsList.appendChild(optionItem);
            });
            
            reviewItem.appendChild(optionsList);
            
            // Add correct answer summary if user got it wrong
            if (!isCorrect) {
                const correctAnswerSummary = document.createElement('div');
                correctAnswerSummary.classList.add('correct-answer-summary');
                
                // Get the correct answer options
                const correctOptions = question.options
                    .filter(option => correctAnswers.includes(option.id))
                    .map(option => `${option.id}`);
                
                correctAnswerSummary.innerHTML = `
                    <strong>Correct Answer${correctOptions.length > 1 ? 's' : ''}:</strong> 
                    <span class="correct">${correctOptions.join(', ')}</span>
                `;
                
                reviewItem.appendChild(correctAnswerSummary);
            }
            
            // Explanation
            if (question.explanation) {
                const explanation = document.createElement('div');
                explanation.classList.add('explanation');
                explanation.innerHTML = `<strong>Explanation:</strong> ${question.explanation}`;
                reviewItem.appendChild(explanation);
            }
            
            reviewQuestionsElement.appendChild(reviewItem);
        });
    }

    // Restart the exam
    function restartExam() {
        // Reset exam time
        examTime = 90 * 60;
        timeElement.textContent = '90:00';
        
        // Hide results screen
        resultsScreen.style.display = 'none';
        
        // Show intro screen
        introScreen.style.display = 'block';
        
        // Reinitialize exam
        initExam();
    }

    // Make initExam globally available for the questions.js file
    window.initExam = initExam;

    // Event listeners
    startBtn.addEventListener('click', startExam);
    
    prevBtn.addEventListener('click', () => {
        currentQuestionIndex--;
        loadQuestion(currentQuestionIndex);
        updateNavButtons();
    });
    
    nextBtn.addEventListener('click', () => {
        currentQuestionIndex++;
        loadQuestion(currentQuestionIndex);
        updateNavButtons();
    });
    
    submitBtn.addEventListener('click', submitExam);
    
    restartBtn.addEventListener('click', restartExam);
});
