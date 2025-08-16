
// Modern Test Handler System
class TestHandler {
    constructor() {
        this.answers = {};
        this.currentSection = null;
        this.testData = null;
        this.timer = null;
        this.startTime = Date.now();
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadTestData();
        this.initializeTimer();
    }

    bindEvents() {
        // Answer selection
        document.addEventListener('click', (e) => {
            if (e.target.closest('.answer-option')) {
                this.selectAnswer(e.target.closest('.answer-option'));
            }
        });

        // Form submission
        document.addEventListener('submit', (e) => {
            if (e.target.id === 'test-form') {
                e.preventDefault();
                this.submitTest();
            }
        });

        // Auto-save on answer change
        document.addEventListener('change', (e) => {
            if (e.target.name && e.target.name.startsWith('question_')) {
                this.saveAnswer(e.target.name, e.target.value);
            }
        });
    }

    selectAnswer(optionElement) {
        const questionContainer = optionElement.closest('.question-container');
        const questionName = optionElement.dataset.question;
        const answerValue = optionElement.dataset.value;

        // Clear previous selections
        questionContainer.querySelectorAll('.answer-option').forEach(opt => {
            opt.classList.remove('selected');
            const radio = opt.querySelector('input[type="radio"]');
            if (radio) radio.checked = false;
        });

        // Select current option
        optionElement.classList.add('selected');
        const radio = optionElement.querySelector('input[type="radio"]');
        if (radio) {
            radio.checked = true;
        }

        // Save answer
        this.saveAnswer(questionName, answerValue);
        
        // Update progress
        this.updateProgress();
    }

    saveAnswer(questionName, value) {
        this.answers[questionName] = value;
        
        // Auto-save to localStorage
        localStorage.setItem(`test_${window.location.pathname}`, JSON.stringify({
            answers: this.answers,
            timestamp: Date.now()
        }));
    }

    updateProgress() {
        const totalQuestions = document.querySelectorAll('.question-container').length;
        const answeredQuestions = Object.keys(this.answers).length;
        const percentage = totalQuestions > 0 ? (answeredQuestions / totalQuestions) * 100 : 0;

        const progressBar = document.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.width = percentage + '%';
            progressBar.textContent = Math.round(percentage) + '%';
        }

        const progressText = document.querySelector('.progress-text');
        if (progressText) {
            progressText.textContent = `${answeredQuestions} of ${totalQuestions} questions answered`;
        }
    }

    calculateScore() {
        const questions = document.querySelectorAll('.question-container');
        let correct = 0;
        let total = 0;

        questions.forEach(question => {
            const questionName = question.dataset.question;
            const correctAnswer = question.dataset.correct;
            
            if (questionName && correctAnswer) {
                total++;
                if (this.answers[questionName] === correctAnswer) {
                    correct++;
                }
            }
        });

        return total > 0 ? (correct / total) * 100 : 0;
    }

    showScore() {
        const score = this.calculateScore();
        const scoreElement = document.querySelector('.current-score');
        
        if (scoreElement) {
            scoreElement.textContent = `Current Score: ${Math.round(score)}%`;
            scoreElement.className = `current-score ${this.getScoreClass(score)}`;
        }
    }

    getScoreClass(score) {
        if (score >= 80) return 'score-excellent';
        if (score >= 60) return 'score-good';
        return 'score-needs-improvement';
    }

    initializeTimer() {
        const timerElement = document.querySelector('.test-timer');
        if (!timerElement) return;

        const duration = parseInt(timerElement.dataset.duration) * 60; // Convert to seconds
        let timeLeft = duration;

        this.timer = setInterval(() => {
            const minutes = Math.floor(timeLeft / 60);
            const seconds = timeLeft % 60;

            timerElement.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

            if (timeLeft <= 300) { // 5 minutes warning
                timerElement.classList.add('timer-warning');
            }

            if (timeLeft <= 0) {
                this.timeUp();
            }

            timeLeft--;
        }, 1000);
    }

    timeUp() {
        clearInterval(this.timer);
        alert('Time is up! Submitting your test automatically.');
        this.submitTest();
    }

    async submitTest() {
        const form = document.getElementById('test-form');
        if (!form) return;

        // Show loading state
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';
        }

        // Prepare form data
        const formData = new FormData();
        
        // Add all answers
        Object.keys(this.answers).forEach(key => {
            formData.append(key, this.answers[key]);
        });

        // Add audio recordings if any
        const audioData = sessionStorage.getItem('audio_recordings');
        if (audioData) {
            formData.append('audio_recordings', audioData);
        }

        try {
            const response = await fetch('/submit-test', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                // Clear saved data
                localStorage.removeItem(`test_${window.location.pathname}`);
                sessionStorage.removeItem('audio_recordings');
                
                // Redirect to results
                window.location.href = response.url;
            } else {
                throw new Error('Submission failed');
            }
        } catch (error) {
            console.error('Test submission error:', error);
            alert('There was an error submitting your test. Please try again.');
            
            // Re-enable submit button
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Submit Test';
            }
        }
    }

    loadTestData() {
        // Load any saved answers
        const saved = localStorage.getItem(`test_${window.location.pathname}`);
        if (saved) {
            try {
                const data = JSON.parse(saved);
                this.answers = data.answers || {};
                this.restoreAnswers();
            } catch (e) {
                console.warn('Failed to load saved answers:', e);
            }
        }
    }

    restoreAnswers() {
        Object.keys(this.answers).forEach(questionName => {
            const value = this.answers[questionName];
            const option = document.querySelector(`[data-question="${questionName}"][data-value="${value}"]`);
            
            if (option) {
                option.classList.add('selected');
                const radio = option.querySelector('input[type="radio"]');
                if (radio) radio.checked = true;
            }
        });
        
        this.updateProgress();
        this.showScore();
    }
}

// Audio Recording Handler
class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.recordings = [];
    }

    async startRecording(questionId) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(stream);
            this.audioChunks = [];

            this.mediaRecorder.ondataavailable = (event) => {
                this.audioChunks.push(event.data);
            };

            this.mediaRecorder.onstop = () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
                this.saveRecording(questionId, audioBlob);
            };

            this.mediaRecorder.start();
            this.isRecording = true;
            this.updateRecordingUI(questionId, 'recording');

        } catch (error) {
            console.error('Error starting recording:', error);
            alert('Could not access microphone. Please check permissions.');
        }
    }

    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            
            // Stop all tracks
            this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
        }
    }

    saveRecording(questionId, audioBlob) {
        const recording = {
            questionId: questionId,
            blob: audioBlob,
            url: URL.createObjectURL(audioBlob),
            timestamp: Date.now()
        };

        this.recordings.push(recording);
        this.updateRecordingUI(questionId, 'completed');
        
        // Save to session storage for form submission
        sessionStorage.setItem('audio_recordings', JSON.stringify(this.recordings.map(r => ({
            questionId: r.questionId,
            timestamp: r.timestamp
        }))));
    }

    updateRecordingUI(questionId, state) {
        const container = document.querySelector(`[data-question-id="${questionId}"]`);
        if (!container) return;

        const startBtn = container.querySelector('.start-recording');
        const stopBtn = container.querySelector('.stop-recording');
        const status = container.querySelector('.recording-status');

        switch (state) {
            case 'recording':
                if (startBtn) startBtn.style.display = 'none';
                if (stopBtn) stopBtn.style.display = 'inline-block';
                if (status) status.textContent = 'Recording...';
                break;
            case 'completed':
                if (startBtn) startBtn.style.display = 'inline-block';
                if (stopBtn) stopBtn.style.display = 'none';
                if (status) status.textContent = 'Recording saved';
                break;
            default:
                if (startBtn) startBtn.style.display = 'inline-block';
                if (stopBtn) stopBtn.style.display = 'none';
                if (status) status.textContent = 'Ready to record';
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.test-interface')) {
        window.testHandler = new TestHandler();
        window.audioRecorder = new AudioRecorder();
    }
});

// Global functions for template use
window.selectAnswer = (questionName, value) => {
    if (window.testHandler) {
        window.testHandler.saveAnswer(questionName, value);
        window.testHandler.updateProgress();
        window.testHandler.showScore();
    }
};

window.startRecording = (questionId) => {
    if (window.audioRecorder) {
        window.audioRecorder.startRecording(questionId);
    }
};

window.stopRecording = () => {
    if (window.audioRecorder) {
        window.audioRecorder.stopRecording();
    }
};
