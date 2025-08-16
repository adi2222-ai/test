# routes.py
import os
import copy
import json
import time
import stripe
from datetime import datetime, timedelta
from flask import (
    render_template, redirect, url_for, flash, request, session, jsonify, current_app, make_response
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from io import BytesIO

from app import app
from forms import LoginForm, RegisterForm
from data_manager import (
    get_user_by_email, create_user, save_test_result, save_mock_test_result, get_user_test_results,
    get_user_mock_test_results, get_vocabulary_words, get_user_vocabulary_progress,
    mark_word_as_learned, test_vocabulary_word, update_user_subscription, get_user_by_id,
    get_test_results, get_test_by_id
)
from test_data_manager import test_manager

# Stripe configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_default')
YOUR_DOMAIN = os.environ.get('REPLIT_DEV_DOMAIN', 'localhost:5000')

DATA_DIR = os.path.join(app.root_path, 'data')
PDF_DIR = os.path.join(app.root_path, 'testspdf')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

# Test content and answers embedded in templates
TEST_ANSWERS = {
    'Reading': {
        'question_1': '2',   # Three times daily
        'question_2': '2',   # Seek immediate medical attention
        'question_3': '1',   # People allergic to penicillin
        'question_4': '1',   # Angioplasty with stents
        'question_5': '1',   # Two weeks
        'question_6': '1',   # April 3, 2024
        'question_7': '3',   # At least four times daily
        'question_8': '1',   # 4.0-7.0 mmol/L
        'question_9': '2',   # 150 minutes
        'question_10': '1'   # To prevent infections and complications
    },
    'Listening': {
        'question_1': '1',   # Mrs. Smith
        'question_2': '2',   # 3 weeks
        'question_3': '1',   # 7 out of 10
        'question_4': '1',   # Ibuprofen
        'question_5': '1',   # Tramadol
        'question_6': '1',   # Up to 40%
        'question_7': '2',   # Five
        'question_8': '1',   # At least 20 seconds
        'question_9': '1',   # 15 seconds
        'question_10': '1'   # Rings and watches
    },
    'Writing': {
        'question_writing': 'manual_grading_required'
    },
    'Speaking': {
        'question_speaking': 'manual_grading_required'
    }
}

# ---------------- Helper functions ----------------
def calculate_dynamic_test_score(answers, test_section, test_data):
    """Calculate score based on test data from new system"""
    if not test_data:
        return 0.0

    # Get questions from test data - try multiple approaches
    questions = []

    # First try to get from complete test content (for practice tests)
    if 'content' in test_data and 'sections' in test_data['content']:
        section_data = test_data['content']['sections'].get(test_section.lower(), {})
        questions = section_data.get('questions', [])

    # If not found, try to get questions from individual section files (for mock tests)
    if not questions:
        try:
            section_content = test_manager.get_test_section(test_data['id'], test_section.lower(), test_data.get('is_mock_test', False))
            if section_content:
                questions = section_content.get('questions', [])
        except Exception as e:
            app.logger.error(f"Error getting test section: {e}")

    # For mock tests with "All Sections", collect questions from all sections
    if not questions and test_section == "All Sections":
        sections_to_check = ['reading', 'listening', 'writing', 'speaking']
        all_questions = []
        
        for section_name in sections_to_check:
            try:
                # First try from complete test content
                if 'content' in test_data and 'sections' in test_data['content']:
                    section_data = test_data['content']['sections'].get(section_name, {})
                    section_questions = section_data.get('questions', [])
                    if section_questions:
                        all_questions.extend(section_questions)
                
                # If not found, try individual section files
                if not section_questions:
                    section_content = test_manager.get_test_section(test_data['id'], section_name, test_data.get('is_mock_test', False))
                    if section_content and section_content.get('questions'):
                        all_questions.extend(section_content['questions'])
            except Exception as e:
                app.logger.error(f"Error getting {section_name} section: {e}")
        
        questions = all_questions

    # Debug logging
    app.logger.info(f"Test {test_data.get('id')}, Section: {test_section}, Questions found: {len(questions)}")
    app.logger.info(f"User answers: {answers}")
    app.logger.info(f"Questions structure: {[q.get('id') for q in questions]}")

    if not questions:
        return 0.0

    total_questions = len(questions)
    correct_count = 0

    for question in questions:
        q_id = question.get('id', 0)
        question_key = f"question_{q_id}"

        app.logger.info(f"Checking question {q_id}: {question_key}")

        if question_key in answers:
            user_answer = answers[question_key]
            q_type = question.get('type', 'multiple_choice')

            app.logger.info(f"Question {q_id}: type={q_type}, user_answer={user_answer}, correct={question.get('correct_answer')}")

            if q_type == 'multiple_choice':
                correct_answer = question.get('correct_answer', 0)
                try:
                    # Convert user answer to integer (0-based indexing)
                    user_answer_int = int(user_answer) if str(user_answer).isdigit() else -1
                    
                    # Ensure correct answer is integer
                    if isinstance(correct_answer, str) and correct_answer.isdigit():
                        correct_answer_int = int(correct_answer)
                    else:
                        correct_answer_int = int(correct_answer) if correct_answer is not None else -1

                    app.logger.info(f"Comparing: user={user_answer_int}, correct={correct_answer_int}")

                    if user_answer_int == correct_answer_int:
                        correct_count += 1
                        app.logger.info(f"Question {q_id}: CORRECT")
                    else:
                        app.logger.info(f"Question {q_id}: INCORRECT - got {user_answer_int}, expected {correct_answer_int}")
                except (ValueError, TypeError) as e:
                    app.logger.error(f"Error converting answers for question {q_id}: {e}")
            elif q_type in ['essay', 'speaking', 'text', 'writing', 'textarea']:
                # Give full credit for text-based answers if they exist and have content
                if user_answer and user_answer.strip() and len(user_answer.strip()) > 20:
                    correct_count += 1  # Full credit for substantial text answers
                    app.logger.info(f"Question {q_id}: TEXT ANSWER - full credit given")
                elif user_answer and user_answer.strip() and len(user_answer.strip()) > 5:
                    correct_count += 0.7  # Partial credit for minimal answers
                    app.logger.info(f"Question {q_id}: TEXT ANSWER - partial credit given")
        else:
            # Also try alternative question key formats
            alt_keys = [f"question_{q_id}", f"q_{q_id}", str(q_id)]
            found_answer = False
            
            for alt_key in alt_keys:
                if alt_key in answers:
                    user_answer = answers[alt_key]
                    q_type = question.get('type', 'multiple_choice')
                    
                    if q_type == 'multiple_choice':
                        correct_answer = question.get('correct_answer', 0)
                        try:
                            user_answer_int = int(user_answer) if str(user_answer).isdigit() else -1
                            correct_answer_int = int(correct_answer) if correct_answer is not None else -1
                            
                            if user_answer_int == correct_answer_int:
                                correct_count += 1
                                app.logger.info(f"Question {q_id}: CORRECT (found with key {alt_key})")
                            else:
                                app.logger.info(f"Question {q_id}: INCORRECT - got {user_answer_int}, expected {correct_answer_int} (key {alt_key})")
                        except (ValueError, TypeError) as e:
                            app.logger.error(f"Error converting answers for question {q_id}: {e}")
                    
                    found_answer = True
                    break
            
            if not found_answer:
                app.logger.info(f"Question {q_id}: NO ANSWER PROVIDED")

    # Calculate percentage: correct answers / total questions * 100
    # This ensures: 1 correct out of 1 = 100%, 1 correct out of 2 = 50%, etc.
    score = (correct_count / total_questions) * 100 if total_questions > 0 else 0.0
    app.logger.info(f"Final score calculation: {correct_count} correct out of {total_questions} total = {score:.1f}%")

    # Ensure score is between 0 and 100
    score = max(0.0, min(100.0, score))
    return round(score, 1)

def calculate_test_score(answers, test_section, test_data=None):
    """Calculate test score based on correct answers"""
    # Always try dynamic scoring first if test_data is provided
    if test_data:
        return calculate_dynamic_test_score(answers, test_section, test_data)
    
    # Fallback to legacy system only if no test_data provided
    if test_section not in TEST_ANSWERS:
        app.logger.warning(f"No test data provided and section {test_section} not in legacy answers")
        return 0.0

    correct_answers = TEST_ANSWERS[test_section]
    total_questions = len(correct_answers)
    correct_count = 0

    app.logger.info(f"Legacy score calculation - Section: {test_section}, Total questions: {total_questions}")
    app.logger.info(f"User answers: {answers}")

    for question_key, correct_answer in correct_answers.items():
        if correct_answer == 'manual_grading_required':
            # For writing/speaking, give partial credit if answer exists
            if question_key in answers and answers[question_key].strip():
                correct_count += 0.7  # 70% credit for attempt
                app.logger.info(f"{question_key}: TEXT ANSWER - partial credit given")
        else:
            if question_key in answers and answers[question_key] == correct_answer:
                correct_count += 1
                app.logger.info(f"{question_key}: CORRECT")
            elif question_key in answers:
                app.logger.info(f"{question_key}: INCORRECT - got {answers[question_key]}, expected {correct_answer}")
            else:
                app.logger.info(f"{question_key}: NO ANSWER PROVIDED")

    # Calculate percentage: correct answers / total questions * 100
    # This ensures: 1 correct out of 1 = 100%, 1 correct out of 2 = 50%, etc.
    score = (correct_count / total_questions) * 100 if total_questions > 0 else 0.0
    app.logger.info(f"Final legacy score: {correct_count} correct out of {total_questions} total = {score:.1f}%")

    # Ensure score is between 0 and 100
    score = max(0.0, min(100.0, score))
    return round(score, 1)

def generate_test_pdf(result, test, user_name, time_taken_minutes):
    """Generate PDF report for test results"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title = Paragraph(f"OET Test Results - {test['title']}", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))

    # User info
    user_info = Paragraph(f"<b>Student:</b> {user_name}", styles['Normal'])
    story.append(user_info)

    completion_time = Paragraph(f"<b>Completed:</b> {result['completed_at']}", styles['Normal'])
    story.append(completion_time)

    time_taken = Paragraph(f"<b>Time Taken:</b> {time_taken_minutes} minutes", styles['Normal'])
    story.append(time_taken)
    story.append(Spacer(1, 12))

    # Score
    score = Paragraph(f"<b>Score:</b> {result['score_percentage']:.1f}%", styles['Heading2'])
    story.append(score)
    story.append(Spacer(1, 12))

    # Performance analysis
    if result['score_percentage'] >= 80:
        performance = "Excellent Performance - Strong understanding demonstrated"
    elif result['score_percentage'] >= 60:
        performance = "Good Performance - On the right track"
    else:
        performance = "Needs Improvement - Consider additional practice"

    perf_text = Paragraph(f"<b>Performance Analysis:</b> {performance}", styles['Normal'])
    story.append(perf_text)
    story.append(Spacer(1, 12))

    # Section breakdown
    section_text = Paragraph(f"<b>Section:</b> {test['section']}", styles['Normal'])
    story.append(section_text)

    # Answer details
    if 'answers' in result and result['answers']:
        story.append(Spacer(1, 12))
        answers_title = Paragraph("<b>Answer Summary:</b>", styles['Heading3'])
        story.append(answers_title)

        for question, answer in result['answers'].items():
            if answer and answer != 'manual_grading_required':
                q_text = Paragraph(f"• {question.replace('_', ' ').title()}: Option {answer}", styles['Normal'])
                story.append(q_text)

    doc.build(story)
    buffer.seek(0)
    return buffer


# ---------------- Routes ----------------
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = get_user_by_email(form.email.data)
        if user and user.password_hash and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        flash('Invalid email or password', 'danger')

    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = RegisterForm()
    if form.validate_on_submit():
        if get_user_by_email(form.email.data):
            flash('Email already registered', 'danger')
            return render_template('register.html', form=form)

        create_user(form.username.data, form.email.data, form.password.data)
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    # Get practice test results
    practice_results = get_user_test_results(current_user.id)
    
    # Get mock test results for this user
    mock_results = get_user_mock_test_results(current_user.id)
    
    # Add test info to mock results
    for result in mock_results:
        test = test_manager.get_complete_test(result.get('test_id'), is_mock=True)
        if test:
            result['test_title'] = test.get('title', f'Test {result["test_id"]}')
            result['test_section'] = test.get('section', 'General')
        result['is_mock'] = True
    
    # Combine all results
    all_results = practice_results + mock_results
    
    # Sort by completed_at and get the most recent 5
    recent_tests = sorted(all_results, key=lambda x: x.get('completed_at', ''), reverse=True)[:5]
    
    vocab_progress = get_user_vocabulary_progress(current_user.id)
    vocab_learned = len(vocab_progress.get('learned_words', [])) if vocab_progress else 0
    
    return render_template('dashboard.html', recent_tests=recent_tests, vocab_learned=vocab_learned, all_test_count=len(all_results))


@app.route('/practice-tests')
@login_required
def practice_tests():
    tests = test_manager.get_all_tests(is_mock=False)
    mock_tests = test_manager.get_all_tests(is_mock=True)
    return render_template('practice_tests.html', tests=tests, mock_tests=mock_tests)


@app.route('/mock-tests')
def mock_tests():
    """Public mock tests page - accessible without login"""
    tests = test_manager.get_all_tests(is_mock=True)
    return render_template('mock_tests.html', tests=tests)


@app.route('/test/<int:test_id>')
def take_test(test_id):
    # Try to find test in both practice and mock tests
    test = test_manager.get_complete_test(test_id, is_mock=False)
    is_mock_test = False

    if not test:
        test = test_manager.get_complete_test(test_id, is_mock=True)
        is_mock_test = True

    if not test:
        flash('Test not found', 'danger')
        return redirect(url_for('practice_tests') if current_user.is_authenticated else url_for('mock_tests'))

    # Set session markers
    session['test_start_time'] = time.time()
    session['current_test_id'] = test_id
    session['mock_test'] = is_mock_test

    # If mock test, allow access even if not logged in
    if is_mock_test:
        return render_template('mock_test_interface.html', test=test)

    # Regular practice test: require login
    if not current_user.is_authenticated:
        flash('Please log in to take this test', 'warning')
        return redirect(url_for('login'))

    # subscription check for premium tests
    if test.get('is_premium', False):
        user_subscription = getattr(current_user, 'subscription_type', None)
        subscription_expires = getattr(current_user, 'subscription_expires', None)

        # Fix datetime comparison issue
        has_active = False
        if user_subscription == 'premium' and subscription_expires:
            try:
                if isinstance(subscription_expires, str):
                    expires_dt = datetime.fromisoformat(subscription_expires)
                else:
                    expires_dt = subscription_expires
                has_active = expires_dt > datetime.utcnow()
            except (ValueError, TypeError):
                has_active = False

        if not has_active:
            flash('This test requires a premium subscription', 'warning')
            return redirect(url_for('subscription'))

    return render_template('practice_test_interface.html', test=test)


@app.route('/submit-test', methods=['POST'])
def submit_test():
    test_id = session.get('current_test_id')
    if not test_id:
        flash('No active test found', 'danger')
        return redirect(url_for('practice_tests') if current_user.is_authenticated else url_for('mock_tests'))

    is_mock = bool(session.get('mock_test', False))

    # If practice test, require login
    if not is_mock and not current_user.is_authenticated:
        flash('Please log in to submit this test.', 'warning')
        return redirect(url_for('login'))

    # Try to find test in both practice and mock tests
    test = test_manager.get_complete_test(test_id, is_mock=False)
    if not test:
        test = test_manager.get_complete_test(test_id, is_mock=True)

    if not test:
        flash('Test not found', 'danger')
        return redirect(url_for('practice_tests'))

    # Collect answers from form
    answers = {}
    for key, value in request.form.items():
        if key.startswith('question_'):
            answers[key] = value

    # Calculate score based on test section
    test_section = test.get('section', 'Reading')
    score_percentage = calculate_test_score(answers, test_section, test)

    # Time taken
    start_time = session.get('test_start_time', time.time())
    time_taken_seconds = int(time.time() - start_time)
    time_taken_minutes = max(1, time_taken_seconds // 60)

    # Determine user_id for saving (None for anonymous mock)
    user_id = current_user.id if (current_user and current_user.is_authenticated) else None

    # Handle audio recordings from speaking sections
    audio_recordings = session.get('audio_recordings', [])
    if audio_recordings:
        answers['audio_recordings'] = audio_recordings

    # Ensure score is a proper float value
    score_percentage = float(score_percentage) if score_percentage is not None else 0.0
    app.logger.info(f"Saving test result with score: {score_percentage}% for {'mock' if is_mock else 'practice'} test")

    # For mock tests, only score multiple choice questions
    if is_mock and answers:
        # Filter answers to only include multiple choice responses (exclude text-based answers)
        mc_answers = {}
        for key, value in answers.items():
            if key.startswith('question_') and isinstance(value, str) and value.isdigit():
                mc_answers[key] = value
        
        # Recalculate score with only multiple choice answers if we have them
        if mc_answers and mc_answers != answers:
            app.logger.info(f"Recalculating mock test score with only MC answers: {mc_answers}")
            score_percentage = calculate_test_score(mc_answers, test_section, test)
            app.logger.info(f"Updated mock test score: {score_percentage}%")

    # Persist to the appropriate JSON file using data_manager functions
    if is_mock:
        result_id = save_mock_test_result(
            user_id=user_id,
            test_id=test_id,
            score_percentage=score_percentage,
            time_taken_minutes=time_taken_minutes,
            answers=answers
        )
    else:
        result_id = save_test_result(
            user_id=user_id,
            test_id=test_id,
            score_percentage=score_percentage,
            time_taken_minutes=time_taken_minutes,
            answers=answers
        )

    # Clear session
    session.pop('test_start_time', None)
    session.pop('current_test_id', None)
    session.pop('mock_test', None)
    session.pop('audio_recordings', None)

    # Save PDF in background for both mock and practice tests
    if is_mock:
        save_mock_test_pdf_background(result_id, test, user_id, time_taken_minutes)
        return redirect(url_for('mock_test_results', result_id=result_id))
    else:
        save_practice_test_pdf_background(result_id, test, user_id, time_taken_minutes)
        return redirect(url_for('test_results', result_id=result_id))

def save_practice_test_pdf_background(result_id, test, user_id, time_taken_minutes):
    """Save practice test PDF to testspdf folder"""
    try:
        all_results = get_test_results()
        result = next((r for r in all_results if r['id'] == result_id), None)
        if not result:
            return

        user_name = "Anonymous User"
        if user_id:
            user = get_user_by_id(user_id)
            if user:
                user_name = user.username

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_buffer = generate_test_pdf(result, test, user_name, time_taken_minutes)

        filename = f"PracticeTest_{test['title']}_{user_name}_{timestamp}.pdf"
        pdf_path = os.path.join(PDF_DIR, filename)

        with open(pdf_path, 'wb') as f:
            f.write(pdf_buffer.read())

        app.logger.info(f"Practice test PDF saved: {filename}")
    except Exception as e:
        app.logger.error(f"Error saving practice test PDF: {e}")


def save_mock_test_pdf_background(result_id, test, user_id, time_taken_minutes):
    """Save mock test PDF to testspdf folder"""
    try:
        from data_manager import get_mock_test_results
        all_results = get_mock_test_results()
        result = next((r for r in all_results if r['id'] == result_id), None)
        if not result:
            return

        user_name = "Anonymous User"
        if user_id:
            user = get_user_by_id(user_id)
            if user:
                user_name = user.username

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_buffer = generate_test_pdf(result, test, user_name, time_taken_minutes)

        filename = f"MockTest_{test['title']}_{user_name}_{timestamp}.pdf"
        pdf_path = os.path.join(PDF_DIR, filename)

        with open(pdf_path, 'wb') as f:
            f.write(pdf_buffer.read())

        app.logger.info(f"Mock test PDF saved: {filename}")
    except Exception as e:
        app.logger.error(f"Error saving mock test PDF: {e}")


@app.route('/results/<int:result_id>')
@login_required
def test_results(result_id):
    # Get all test results and find the specific one
    all_results = get_test_results()
    result = next((r for r in all_results if r['id'] == result_id and r.get('user_id') == current_user.id), None)

    if not result:
        flash('Test result not found', 'danger')
        return redirect(url_for('dashboard'))

    # Get the test data from new system first
    test = test_manager.get_complete_test(result['test_id'], is_mock=False)
    if not test:
        # Try mock tests
        test = test_manager.get_complete_test(result['test_id'], is_mock=True)
    if not test:
        # Fallback to old system
        test = get_test_by_id(result['test_id'])

    if not test:
        # Create a basic test object if not found
        test = {
            'id': result['test_id'],
            'title': f'Test {result["test_id"]}',
            'section': 'Unknown',
            'description': 'Test completed'
        }

    return render_template('practice_test_results.html', result=result, test=test)


@app.route('/mock-results/<int:result_id>')
def mock_test_results(result_id):
    # Public mock result viewer - load from mock tests results
    from data_manager import get_mock_test_results
    all_results = get_mock_test_results()
    result = next((r for r in all_results if r['id'] == result_id), None)
    if not result:
        flash('Mock result not found', 'danger')
        return redirect(url_for('mock_tests'))
    test = test_manager.get_complete_test(result['test_id'], is_mock=True)
    if not test:
        test = test_manager.get_complete_test(result['test_id'], is_mock=False)
    return render_template('mock_test_results.html', result=result, test=test)


@app.route('/download-pdf/<int:result_id>')
@login_required
def download_test_pdf(result_id):
    user_results = get_user_test_results(current_user.id)
    result = next((r for r in user_results if r['id'] == result_id), None)
    if not result:
        flash('Test result not found', 'danger')
        return redirect(url_for('dashboard'))

    test = test_manager.get_complete_test(result['test_id'], is_mock=False)
    if not test:
        test = test_manager.get_complete_test(result['test_id'], is_mock=True)
    time_taken = result.get('time_taken_minutes', 0)
    pdf_buffer = generate_test_pdf(result, test, current_user.username, time_taken)

    response = make_response(pdf_buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="{test["title"]}_{current_user.username}_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf"'

    return response


@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    """Handle audio uploads from speaking sections"""
    try:
        if 'audio_data' not in request.files:
            return jsonify({'error': 'No audio data provided'}), 400

        audio_file = request.files['audio_data']
        if audio_file.filename == '':
            return jsonify({'error': 'No audio file selected'}), 400

        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(app.root_path, 'uploads', 'audio')
        os.makedirs(upload_dir, exist_ok=True)

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_id = current_user.id if current_user.is_authenticated else 'anonymous'
        filename = f"speaking_{user_id}_{timestamp}.webm"
        filepath = os.path.join(upload_dir, filename)

        # Save the audio file
        audio_file.save(filepath)

        # Store the file path in session for later use during test submission
        if 'audio_recordings' not in session:
            session['audio_recordings'] = []
        session['audio_recordings'].append({
            'filename': filename,
            'filepath': filepath,
            'timestamp': timestamp
        })

        app.logger.info(f"Audio file saved: {filename}")
        return jsonify({'success': True, 'filename': filename}), 200

    except Exception as e:
        app.logger.error(f"Error uploading audio: {e}")
        return jsonify({'error': 'Failed to upload audio'}), 500


@app.route('/download-mock-pdf/<int:result_id>')
def download_mock_pdf(result_id):
    from data_manager import get_mock_test_results
    all_results = get_mock_test_results()
    result = next((r for r in all_results if r['id'] == result_id), None)
    if not result:
        flash('Mock result not found', 'danger')
        return redirect(url_for('mock_tests'))

    test = test_manager.get_complete_test(result['test_id'], is_mock=True)
    if not test:
        test = test_manager.get_complete_test(result['test_id'], is_mock=False)
    user_name = "Anonymous User"
    if result.get('user_id') and current_user.is_authenticated and current_user.id == result['user_id']:
        user_name = current_user.username

    time_taken = result.get('time_taken_minutes', 0)
    pdf_buffer = generate_test_pdf(result, test, user_name, time_taken)

    response = make_response(pdf_buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="{test["title"]}_{user_name}_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf"'

    return response


# ---------- remaining routes (unchanged behavior) ----------
@app.route('/progress')
@login_required
def progress():
    test_results = get_user_test_results(current_user.id)
    vocab_progress = get_user_vocabulary_progress(current_user.id)
    vocab_count = len(vocab_progress.get('learned_words', [])) if vocab_progress else 0
    total_vocab = len(get_vocabulary_words())
    return render_template('progress.html', test_results=test_results, vocab_count=vocab_count, total_vocab=total_vocab)


@app.route('/vocabulary')
@login_required
def vocabulary():
    specialty = request.args.get('specialty', 'all')
    words = get_vocabulary_words(specialty if specialty != 'all' else None)
    vocab_progress = get_user_vocabulary_progress(current_user.id)
    learned_word_ids = vocab_progress.get('learned_words', [])
    all_words = get_vocabulary_words()
    specialties = sorted(set(word.get('specialty') for word in all_words if word.get('specialty')))
    return render_template('vocabulary.html', words=words, learned_word_ids=learned_word_ids, specialties=[(s,) for s in specialties], selected_specialty=specialty)


@app.route('/vocabulary-test', methods=['POST'])
@login_required
def vocabulary_test():
    data = request.get_json()
    word = data.get('word', '').strip()
    result = test_vocabulary_word(word)
    return jsonify(result)


@app.route('/mark-word-learned/<int:word_id>', methods=['POST'])
@login_required
def mark_word_learned(word_id):
    success = mark_word_as_learned(current_user.id, word_id)
    return jsonify({'success': success})


@app.route('/subscription')
@login_required
def subscription():
    return render_template('subscription.html')




@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    plan = request.form.get('plan')
    plans = {
        'monthly': 'https://buy.stripe.com/test_6oU28t7UU0woeed2nJc3m00',
        'yearly': 'https://buy.stripe.com/test_6oU28t7UU0woeed2nJc3m00'
    }
    if plan not in plans:
        flash('Invalid subscription plan', 'danger')
        return redirect(url_for('subscription'))
    return redirect(plans[plan])


@app.route('/subscription-success')
@login_required
def subscription_success():
    session_id = request.args.get('session_id')
    if session_id:
        try:
            session_obj = stripe.checkout.Session.retrieve(session_id)
            if session_obj.payment_status == 'paid':
                subscription_type = 'premium'
                expires_at = datetime.utcnow() + timedelta(days=30)
                if session_obj.subscription:
                    subscription = stripe.Subscription.retrieve(str(session_obj.subscription))
                    if getattr(subscription, 'current_period_end', None):
                        expires_at = datetime.fromtimestamp(subscription.current_period_end)
                update_user_subscription(current_user.id, subscription_type, expires_at)
                flash('Subscription activated! Thank you!', 'success')
                return redirect(url_for('dashboard'))
        except Exception as e:
            app.logger.error(f"Stripe subscription retrieval error: {e}")
    flash('Subscription could not be verified. Please contact support.', 'danger')
    return redirect(url_for('subscription'))


@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return 'Invalid payload', 400
    except Exception:
        return 'Invalid signature', 400

    if event['type'] == 'customer.subscription.updated':
        app.logger.info('subscription.updated event received')
    elif event['type'] == 'customer.subscription.deleted':
        app.logger.info('subscription.deleted event received')

    return 'Success', 200


@app.route('/consultation')
def consultation():
    return render_template('consultation.html')


@app.route('/jobs')
def jobs():
    from data_manager import get_active_jobs
    jobs_list = get_active_jobs()
    return render_template('jobs.html', jobs=jobs_list)


@app.route('/admin/jobs')
@login_required
def admin_jobs():
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    from data_manager import get_jobs
    jobs_list = get_jobs()
    return render_template('admin_jobs.html', jobs=jobs_list)


@app.route('/admin/jobs/add', methods=['GET', 'POST'])
@login_required
def admin_add_job():
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        from data_manager import create_job

        title = request.form.get('title', '').strip()
        company = request.form.get('company', '').strip()
        location = request.form.get('location', '').strip()
        job_type = request.form.get('job_type', '').strip()
        salary_range = request.form.get('salary_range', '').strip()
        description = request.form.get('description', '').strip()
        requirements = request.form.get('requirements', '').strip()
        contact_email = request.form.get('contact_email', '').strip()

        if title and company and location and description:
            job_id = create_job(title, company, location, job_type, salary_range, description, requirements, contact_email)
            if job_id:
                flash('Job posted successfully!', 'success')
                return redirect(url_for('admin_jobs'))
            else:
                flash('Error posting job.', 'danger')
        else:
            flash('Title, company, location, and description are required.', 'danger')

    return render_template('admin_add_job.html')


@app.route('/admin/jobs/edit/<int:job_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_job(job_id):
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    from data_manager import get_job_by_id, update_job

    job = get_job_by_id(job_id)
    if not job:
        flash('Job not found.', 'danger')
        return redirect(url_for('admin_jobs'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        company = request.form.get('company', '').strip()
        location = request.form.get('location', '').strip()
        job_type = request.form.get('job_type', '').strip()
        salary_range = request.form.get('salary_range', '').strip()
        description = request.form.get('description', '').strip()
        requirements = request.form.get('requirements', '').strip()
        contact_email = request.form.get('contact_email', '').strip()
        is_active = 'is_active' in request.form

        if title and company and location and description:
            success = update_job(job_id, title, company, location, job_type, salary_range, description, requirements, contact_email, is_active)
            if success:
                flash('Job updated successfully!', 'success')
                return redirect(url_for('admin_jobs'))
            else:
                flash('Error updating job.', 'danger')
        else:
            flash('Title, company, location, and description are required.', 'danger')

    return render_template('admin_edit_job.html', job=job)


@app.route('/admin/jobs/delete/<int:job_id>', methods=['POST'])
@login_required
def admin_delete_job(job_id):
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    from data_manager import delete_job

    success = delete_job(job_id)
    if success:
        flash('Job deleted successfully!', 'success')
    else:
        flash('Error deleting job.', 'danger')

    return redirect(url_for('admin_jobs'))


@app.route('/job/<int:job_id>')
def job_detail(job_id):
    from data_manager import get_job_by_id
    job = get_job_by_id(job_id)
    if not job or not job.get('is_active', True):
        flash('Job not found or no longer available.', 'danger')
        return redirect(url_for('jobs'))
    return render_template('job_detail.html', job=job)


@app.route('/materials')
def materials():
    return render_template('materials.html')


# Super User Routes
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    from data_manager import get_all_chat_messages
    chat_messages = get_all_chat_messages()
    unread_messages = [msg for msg in chat_messages if not msg['is_read'] and not msg['is_admin_reply']]

    return render_template('admin_dashboard.html', unread_messages=unread_messages)


@app.route('/admin/search-users')
@login_required
def search_users():
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    search_term = request.args.get('search', '')
    users = []

    if search_term:
        from data_manager import search_users_by_name
        users = search_users_by_name(search_term)

    return render_template('admin_users.html', users=users, search_term=search_term)


@app.route('/admin/user/<int:user_id>')
@login_required
def admin_user_detail(user_id):
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    user = get_user_by_id(user_id)
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('search_users'))

    test_results = get_user_test_results(user_id)
    mock_results = get_user_mock_test_results(user_id)
    vocab_progress = get_user_vocabulary_progress(user_id)

    return render_template('admin_user_detail.html', 
                         user=user, 
                         test_results=test_results,
                         mock_results=mock_results,
                         vocab_progress=vocab_progress)


# Chat Routes
@app.route('/chat')
@login_required
def chat():
    from data_manager import get_user_chat_messages
    messages = get_user_chat_messages(current_user.id)
    return render_template('chat.html', messages=messages)


@app.route('/send-message', methods=['POST'])
@login_required
def send_message():
    message = request.form.get('message', '').strip()
    if message:
        from data_manager import add_chat_message
        add_chat_message(current_user.id, current_user.username, message)
        flash('Message sent successfully!', 'success')
    return redirect(url_for('chat'))


@app.route('/admin/chat')
@login_required
def admin_chat():
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    from data_manager import get_all_chat_messages
    messages = get_all_chat_messages()
    return render_template('admin_chat.html', messages=messages)


@app.route('/admin/reply-message', methods=['POST'])
@login_required
def admin_reply_message():
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    user_id = request.form.get('user_id')
    reply_message = request.form.get('reply_message', '').strip()

    if user_id and reply_message:
        user = get_user_by_id(int(user_id))
        if user:
            from data_manager import add_chat_message
            add_chat_message(int(user_id), f"Admin Reply to {user.username}", reply_message, is_admin_reply=True)
            flash('Reply sent successfully!', 'success')

    return redirect(url_for('admin_chat'))


@app.route('/admin/mark-read/<int:message_id>')
@login_required
def mark_message_read(message_id):
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    from data_manager import mark_message_as_read
    mark_message_as_read(message_id)
    return redirect(url_for('admin_chat'))


@app.route('/admin/tests')
@login_required
def admin_tests():
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    practice_tests = test_manager.get_all_tests(is_mock=False)
    mock_tests = test_manager.get_all_tests(is_mock=True)
    all_tests = practice_tests + mock_tests

    # Add test statistics
    stats = test_manager.get_test_statistics()

    return render_template('admin_tests.html', all_tests=all_tests, stats=stats)


@app.route('/admin/edit-test/<int:test_id>')
@login_required
def admin_edit_test(test_id):
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    # Try to find test in both practice and mock tests
    test = test_manager.get_complete_test(test_id, is_mock=False)
    is_mock = False
    if not test:
        test = test_manager.get_complete_test(test_id, is_mock=True)
        is_mock = True

    if not test:
        flash('Test not found', 'danger')
        return redirect(url_for('admin_tests'))

    return render_template('admin_edit_test.html', test=test, is_mock=is_mock)


@app.route('/admin/save-test/<int:test_id>', methods=['POST'])
@login_required
def admin_save_test(test_id):
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    # Check if test exists and determine if it's mock or practice
    test = test_manager.get_complete_test(test_id, is_mock=False)
    is_mock = False
    if not test:
        test = test_manager.get_complete_test(test_id, is_mock=True)
        is_mock = True

    if not test:
        flash('Test not found', 'danger')
        return redirect(url_for('admin_tests'))

    # Get form data
    form_data = request.form.to_dict()

    # Update metadata
    metadata = {
        'id': test_id,
        'title': form_data.get('title'),
        'section': form_data.get('section'),
        'duration_minutes': int(form_data.get('duration_minutes', 0)),
        'description': form_data.get('description'),
        'is_mock_test': 'is_mock_test' in form_data,
        'is_premium': 'is_premium' in form_data,
        'created_at': test.get('created_at', datetime.now().isoformat())
    }

    # Save metadata
    success = test_manager.update_test_metadata(test_id, metadata, is_mock)
    if not success:
        flash('Error updating test metadata.', 'danger')
        return redirect(url_for('admin_edit_test', test_id=test_id))

    # Process and save each section
    section_types = ['reading', 'listening', 'writing', 'speaking']

    for section_name in section_types:
        section_data = test_manager._get_default_section_content(section_name)

        # Basic section info
        duration_key = f"{section_name}_duration"
        if duration_key in form_data:
            section_data['duration_minutes'] = int(form_data.get(duration_key, 0))

        # Handle passages for reading section
        if section_name == 'reading':
            passages = []
            passage_ids = set()

            for key in form_data.keys():
                if key.startswith(f"{section_name}_passage_") and key.endswith('_title'):
                    passage_id = key.split('_')[2]
                    passage_ids.add(passage_id)

            for p_id in sorted(passage_ids):
                title = form_data.get(f"{section_name}_passage_{p_id}_title")
                content_text = form_data.get(f"{section_name}_passage_{p_id}_content")

                if title or content_text:
                    passages.append({
                        'id': int(p_id) if p_id.isdigit() else len(passages),
                        'title': title or f"Passage {len(passages) + 1}",
                        'content': content_text or ''
                    })

            section_data['passages'] = passages

        # Handle audio files for listening section
        if section_name == 'listening':
            audio_files = []
            audio_ids = set()

            for key in form_data.keys():
                if key.startswith(f"{section_name}_audio_") and key.endswith('_title'):
                    audio_id = key.split('_')[2]
                    audio_ids.add(audio_id)

            for a_id in sorted(audio_ids):
                title = form_data.get(f"{section_name}_audio_{a_id}_title")
                url = form_data.get(f"{section_name}_audio_{a_id}_url")
                transcript = form_data.get(f"{section_name}_audio_{a_id}_transcript")

                if title or url:
                    audio_files.append({
                        'id': int(a_id) if a_id.isdigit() else len(audio_files),
                        'title': title or f"Audio {len(audio_files) + 1}",
                        'url': url or '',
                        'transcript': transcript or ''
                    })

            section_data['audio_files'] = audio_files

        # Handle questions for all sections
        questions = []
        question_ids = set()

        for key in form_data.keys():
            if key.startswith(f"{section_name}_question_") and key.endswith('_text'):
                question_id = key.split('_')[2]
                question_ids.add(question_id)

        for q_id in sorted(question_ids):
            question_text = form_data.get(f"{section_name}_question_{q_id}_text")
            question_type = form_data.get(f"{section_name}_question_{q_id}_type")

            if question_text:
                question = {
                    'id': int(q_id) if q_id.isdigit() else len(questions) + 1,
                    'question': question_text,
                    'type': question_type
                }

                if question_type == 'multiple_choice':
                    options = []
                    option_index = 0
                    while True:
                        option_key = f"{section_name}_question_{q_id}_option_{option_index}"
                        if option_key in form_data and form_data[option_key].strip():
                            options.append(form_data[option_key].strip())
                            option_index += 1
                        else:
                            break

                    correct_answer = form_data.get(f"{section_name}_question_{q_id}_correct", '0')

                    question['options'] = options
                    try:
                        question['correct_answer'] = int(correct_answer)
                    except ValueError:
                        question['correct_answer'] = 0
                else:
                    text_correct_key = f"{section_name}_question_{q_id}_text_correct"
                    question['correct_answer'] = form_data.get(text_correct_key, '')

                questions.append(question)

        section_data['questions'] = questions

        # Handle writing scenario
        if section_name == 'writing':
            scenario = {}
            scenario_fields = ['patient_name', 'age', 'presenting_complaint', 'examination_findings', 'referral_to', 'task_instructions']

            for field in scenario_fields:
                field_key = f"{section_name}_{field}"
                if field_key in form_data and form_data[field_key].strip():
                    scenario[field] = form_data[field_key].strip()

            section_data['scenario'] = scenario

        # Handle speaking role plays
        if section_name == 'speaking':
            role_plays = []
            roleplay_ids = set()

            for key in form_data.keys():
                if key.startswith(f"{section_name}_roleplay_") and '_setting' in key:
                    roleplay_id = key.split('_')[2]
                    roleplay_ids.add(roleplay_id)

            for rp_id in sorted(roleplay_ids):
                setting = form_data.get(f"{section_name}_roleplay_{rp_id}_setting")
                your_role = form_data.get(f"{section_name}_roleplay_{rp_id}_your_role")
                patient = form_data.get(f"{section_name}_roleplay_{rp_id}_patient")
                task = form_data.get(f"{section_name}_roleplay_{rp_id}_task")

                if setting or your_role:
                    role_plays.append({
                        'id': int(rp_id) if rp_id.isdigit() else len(role_plays) + 1,
                        'setting': setting or '',
                        'your_role': your_role or '',
                        'patient': patient or '',
                        'task': task or '',
                        'time_limit': 5
                    })

            section_data['role_plays'] = role_plays

        # Save section data
        test_manager.update_test_section(test_id, section_name, section_data, is_mock)

    flash('Test updated successfully!', 'success')
    return redirect(url_for('admin_edit_test', test_id=test_id))


@app.route('/admin/vocabulary')
@login_required
def admin_vocabulary():
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    words = get_vocabulary_words()
    return render_template('admin_vocabulary.html', words=words)


@app.route('/admin/vocabulary/add', methods=['GET', 'POST'])
@login_required
def admin_add_vocabulary():
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        from data_manager import add_vocabulary_word

        word = request.form.get('word', '').strip()
        definition = request.form.get('definition', '').strip()
        specialty = request.form.get('specialty', '').strip()

        if word and definition:
            success = add_vocabulary_word(word, definition, specialty)
            if success:
                flash('Vocabulary word added successfully!', 'success')
            else:
                flash('Error adding vocabulary word.', 'danger')
        else:
            flash('Word and definition are required.', 'danger')

        return redirect(url_for('admin_vocabulary'))

    return render_template('admin_add_vocabulary.html')


@app.route('/admin/vocabulary/edit/<int:word_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_vocabulary(word_id):
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    from data_manager import get_vocabulary_word_by_id, update_vocabulary_word

    word_data = get_vocabulary_word_by_id(word_id)
    if not word_data:
        flash('Vocabulary word not found.', 'danger')
        return redirect(url_for('admin_vocabulary'))

    if request.method == 'POST':
        word = request.form.get('word', '').strip()
        definition = request.form.get('definition', '').strip()
        specialty = request.form.get('specialty', '').strip()

        if word and definition:
            success = update_vocabulary_word(word_id, word, definition, specialty)
            if success:
                flash('Vocabulary word updated successfully!', 'success')
            else:
                flash('Error updating vocabulary word.', 'danger')
        else:
            flash('Word and definition are required.', 'danger')

        return redirect(url_for('admin_vocabulary'))

    return render_template('admin_edit_vocabulary.html', word_data=word_data)


@app.route('/admin/vocabulary/delete/<int:word_id>', methods=['POST'])
@login_required
def admin_delete_vocabulary(word_id):
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    from data_manager import delete_vocabulary_word

    success = delete_vocabulary_word(word_id)
    if success:
        flash('Vocabulary word deleted successfully!', 'success')
    else:
        flash('Error deleting vocabulary word.', 'danger')

    return redirect(url_for('admin_vocabulary'))


@app.route('/admin/create-test', methods=['GET', 'POST'])
@login_required
def admin_create_test():
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        section = request.form.get('section', 'Reading')
        duration = int(request.form.get('duration_minutes', 60))
        description = request.form.get('description', '').strip()
        is_mock = 'is_mock_test' in request.form
        is_premium = 'is_premium' in request.form

        if title:
            test_id = test_manager.create_test(title, section, duration, description, is_mock, is_premium)
            if test_id:
                flash('Test created successfully!', 'success')
                return redirect(url_for('admin_edit_test', test_id=test_id))
            else:
                flash('Error creating test.', 'danger')
        else:
            flash('Test title is required.', 'danger')

    return render_template('admin_create_test.html')


@app.route('/admin/delete-test/<int:test_id>', methods=['POST'])
@login_required
def admin_delete_test(test_id):
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    # Try to delete from both practice and mock tests
    success = test_manager.delete_test(test_id, is_mock=False)
    if not success:
        success = test_manager.delete_test(test_id, is_mock=True)

    if success:
        flash('Test deleted successfully!', 'success')
    else:
        flash('Error deleting test.', 'danger')

    return redirect(url_for('admin_tests'))


# Error handlers
@app.errorhandler(404)
def page_not_found(error):
    """Handle 404 errors"""
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_server_error(error):
    """Handle 500 errors"""
    app.logger.error(f'Server Error: {error}')
    return render_template('errors/500.html'), 500


@app.errorhandler(403)
def forbidden(error):
    """Handle 403 errors"""
    return render_template('errors/403.html'), 403



@app.route('/admin/duplicate-test/<int:test_id>', methods=['POST'])
@login_required
def admin_duplicate_test(test_id):
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    new_title = request.form.get('new_title', '').strip()
    if not new_title:
        flash('New test title is required.', 'danger')
        return redirect(url_for('admin_tests'))

    # Check if source is mock or practice test
    source_test = test_manager.get_complete_test(test_id, is_mock=False)
    source_is_mock = False
    if not source_test:
        source_test = test_manager.get_complete_test(test_id, is_mock=True)
        source_is_mock = True

    if not source_test:
        flash('Source test not found.', 'danger')
        return redirect(url_for('admin_tests'))

    target_is_mock = 'target_mock' in request.form

    new_test_id = test_manager.duplicate_test(test_id, new_title, source_is_mock, target_is_mock)

    if new_test_id:
        flash(f'Test duplicated successfully! New test ID: {new_test_id}', 'success')
        return redirect(url_for('admin_edit_test', test_id=new_test_id))
    else:
        flash('Error duplicating test.', 'danger')
        return redirect(url_for('admin_tests'))




@app.route('/admin/section-manager/<int:test_id>')
@login_required
def admin_section_manager(test_id):
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    # Try to find test in both practice and mock tests
    test = test_manager.get_complete_test(test_id, is_mock=False)
    if not test:
        test = test_manager.get_complete_test(test_id, is_mock=True)

    if not test:
        flash('Test not found', 'danger')
        return redirect(url_for('admin_tests'))

    return render_template('admin_section_manager.html', test=test)




@app.route('/api/test-stats')
@login_required
def api_test_stats():
    if not current_user.is_super_user():
        return jsonify({'error': 'Access denied'}), 403

    stats = test_manager.get_test_statistics()
    return jsonify(stats)




@app.route('/admin/migration')
@login_required
def admin_migration():
    if not current_user.is_super_user():
        flash('Access denied. Super user privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    return render_template('admin_migration.html')