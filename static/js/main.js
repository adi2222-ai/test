// static/js/main.js
// OET Preparation Platform - Main JavaScript (updated)
// Combines global app initialization + test navigation/progress + utilities

// Global variables
let currentUser = null;
let testSession = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('%c🏥 OET Preparation Platform', 'color: #0d6efd; font-size: 20px; font-weight: bold;');
    console.log('%cWelcome to the OET Preparation Platform! Good luck with your studies.', 'color: #198754; font-size: 14px;');

    // Test interface functionality
    initializeTestInterface();

    // Initialize other page-specific functionality
    initializeGeneralPageFunctionality();
});

function initializeGeneralPageFunctionality() {
    console.log('Initializing general page functionality...');

    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Test answer validation
    initializeAnswerValidation();

    console.log('OET Preparation Platform initialized successfully');
}

function initializeAnswerValidation() {
    // Make radio button labels clickable for better UX
    const radioLabels = document.querySelectorAll('label[for^="q"], label[for^="r"]');
    radioLabels.forEach(label => {
        label.style.cursor = 'pointer';
        label.addEventListener('click', function() {
            const input = document.getElementById(this.getAttribute('for'));
            if (input && input.type === 'radio') {
                input.checked = true;
                // Trigger change event for any listeners
                input.dispatchEvent(new Event('change'));
            }
        });
    });
}

function initializeTestInterface() {
    console.log('Initializing test interface...');

    // Test submission validation
    const testForm = document.getElementById('testForm');
    if (testForm) {
        testForm.addEventListener('submit', function(e) {
            if (!validateTestAnswers()) {
                e.preventDefault();
                alert('Please answer all questions before submitting the test.');
                return false;
            }
        });
    }

    // Word count for writing sections
    const writingTextarea = document.querySelector('textarea[name*="writing"]');
    if (writingTextarea) {
        initializeWordCount(writingTextarea);
    }
}

function validateTestAnswers() {
    const questions = document.querySelectorAll('input[name^="question_"], textarea[name^="question_"]');
    let unanswered = 0;

    const questionGroups = new Set();
    questions.forEach(q => {
        questionGroups.add(q.name);
    });

    questionGroups.forEach(groupName => {
        const groupQuestions = document.querySelectorAll(`[name="${groupName}"]`);
        let hasAnswer = false;

        groupQuestions.forEach(q => {
            if (q.type === 'radio' && q.checked) {
                hasAnswer = true;
            } else if (q.type !== 'radio' && q.value.trim()) {
                hasAnswer = true;
            }
        });

        if (!hasAnswer) {
            unanswered++;
        }
    });

    return unanswered === 0;
}

function initializeWordCount(textarea) {
    const wordCountDisplay = document.getElementById('wordCount');
    if (!wordCountDisplay) return;

    function updateWordCount() {
        const text = textarea.value.trim();
        const wordCount = text === '' ? 0 : text.split(/\s+/).length;
        wordCountDisplay.textContent = wordCount;

        // Color coding for word count
        if (wordCount < 150) {
            wordCountDisplay.className = 'text-warning';
        } else if (wordCount > 220) {
            wordCountDisplay.className = 'text-danger';
        } else {
            wordCountDisplay.className = 'text-success';
        }
    }

    textarea.addEventListener('input', updateWordCount);
    updateWordCount(); // Initial count
}

// Export functions for use in other scripts
window.OETApp = {
    showNotification: typeof showNotification !== 'undefined' ? showNotification : () => {}, // Ensure functions exist
    updateProgress: typeof updateProgress !== 'undefined' ? updateProgress : () => {},
    selectAnswer: typeof selectAnswer !== 'undefined' ? selectAnswer : () => {}
};