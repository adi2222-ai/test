# data_manager.py
import json
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from flask_login import UserMixin

# Data file paths
DATA_DIR = 'data'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
PRACTICE_TESTS_FILE = os.path.join(DATA_DIR, 'practice_tests.json')
FULL_MOCK_TESTS_FILE = os.path.join(DATA_DIR, 'full_mock_tests.json')
MOCK_TESTS_FILE = os.path.join(DATA_DIR, 'full_mock_tests.json')
TEST_RESULTS_FILE = os.path.join(DATA_DIR, 'test_results.json')
MOCK_TEST_RESULTS_FILE = os.path.join(DATA_DIR, 'mocktests_results.json')
VOCABULARY_FILE = os.path.join(DATA_DIR, 'vocabulary.json')
VOCABULARY_PROGRESS_FILE = os.path.join(DATA_DIR, 'vocabulary_progress.json')
JOBS_FILE = os.path.join(DATA_DIR, 'jobs.json')

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

class User(UserMixin):
    def __init__(self, id, username, email, password_hash, subscription_type=None, subscription_expires=None, is_superuser=False):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.subscription_type = subscription_type
        self.subscription_expires = subscription_expires
        self.is_superuser = is_superuser

    def has_active_subscription(self):
        if not self.subscription_type or not self.subscription_expires:
            return False
        try:
            return datetime.fromisoformat(self.subscription_expires) > datetime.now()
        except:
            return False

    def is_super_user(self):
        return self.is_superuser

def load_json_file(filepath, default=None):
    if default is None:
        default = []
    if not os.path.exists(filepath):
        save_json_file(filepath, default)
        return default
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default

def save_json_file(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_next_id(data_list):
    if not data_list:
        return 1
    return max(item['id'] for item in data_list) + 1

# User management
def get_users():
    return load_json_file(USERS_FILE, [])

def save_users(users):
    save_json_file(USERS_FILE, users)

def get_user_by_email(email):
    users = get_users()
    for user_data in users:
        if user_data['email'] == email:
            return User(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                subscription_type=user_data.get('subscription_type'),
                subscription_expires=user_data.get('subscription_expires'),
                is_superuser=user_data.get('is_superuser', False)
            )
    return None

def get_user_by_id(user_id):
    users = get_users()
    for user_data in users:
        if user_data['id'] == user_id:
            return User(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                subscription_type=user_data.get('subscription_type'),
                subscription_expires=user_data.get('subscription_expires'),
                is_superuser=user_data.get('is_superuser', False)
            )
    return None

def search_users_by_name(search_term):
    """Search users by username containing the search term"""
    users = get_users()
    matching_users = []
    for user_data in users:
        if search_term.lower() in user_data['username'].lower():
            matching_users.append(User(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                subscription_type=user_data.get('subscription_type'),
                subscription_expires=user_data.get('subscription_expires'),
                is_superuser=user_data.get('is_superuser', False)
            ))
    return matching_users

def create_user(username, email, password):
    users = get_users()
    user_id = get_next_id(users)
    user_data = {
        'id': user_id,
        'username': username,
        'email': email,
        'password_hash': generate_password_hash(password),
        'subscription_type': None,
        'subscription_expires': None,
        'created_at': datetime.now().isoformat()
    }
    users.append(user_data)
    save_users(users)
    return User(id=user_id, username=username, email=email, password_hash=user_data['password_hash'])

def update_user_subscription(user_id, subscription_type, expires_at):
    users = get_users()
    for user in users:
        if user['id'] == user_id:
            user['subscription_type'] = subscription_type
            user['subscription_expires'] = expires_at.isoformat()
            break
    save_users(users)

# Test management - using hardcoded test definitions
def get_practice_tests():
    return load_json_file(PRACTICE_TESTS_FILE, [
        {
            'id': 1,
            'title': 'Listening Practice Test 1',
            'section': 'Listening',
            'duration_minutes': 30,
            'description': 'Basic listening comprehension test',
            'is_premium': False,
            'content': {
                'sections': {
                    'listening': {
                        'duration_minutes': 30,
                        'passages': [],
                        'questions': []
                    }
                }
            }
        },
        {
            'id': 2,
            'title': 'Reading Practice Test 1',
            'section': 'Reading',
            'duration_minutes': 45,
            'description': 'Reading comprehension and analysis',
            'is_premium': False,
            'content': {
                'sections': {
                    'reading': {
                        'duration_minutes': 45,
                        'passages': [],
                        'questions': []
                    }
                }
            }
        },
        {
            'id': 3,
            'title': 'Writing Practice Test 1',
            'section': 'Writing',
            'duration_minutes': 45,
            'description': 'Letter writing task',
            'is_premium': True,
            'content': {
                'sections': {
                    'writing': {
                        'duration_minutes': 45,
                        'passages': [],
                        'questions': []
                    }
                }
            }
        },
        {
            'id': 4,
            'title': 'Speaking Practice Test 1',
            'section': 'Speaking',
            'duration_minutes': 20,
            'description': 'Role-play scenarios',
            'is_premium': True,
            'content': {
                'sections': {
                    'speaking': {
                        'duration_minutes': 20,
                        'passages': [],
                        'questions': []
                    }
                }
            }
        }
    ])

def get_full_mock_tests():
    return load_json_file(MOCK_TESTS_FILE, [
        {
            'id': 100,
            'title': 'Complete OET Mock Test 1',
            'section': 'All Sections',
            'duration_minutes': 180,
            'description': 'Full OET practice exam covering all sections',
            'is_mock_test': True,
            'is_premium': False,
            'content': {
                'sections': {
                    'reading': {
                        'duration_minutes': 45,
                        'passages': [
                            {
                                'id': 1,
                                'title': 'Patient Care Guidelines',
                                'content': 'Comprehensive patient care guidelines for healthcare professionals...'
                            }
                        ],
                        'questions': [
                            {
                                'id': 1,
                                'question': 'What is the primary focus of patient care?',
                                'type': 'multiple_choice',
                                'options': ['Safety', 'Efficiency', 'Cost', 'Speed'],
                                'correct_answer': 0
                            }
                        ]
                    },
                    'listening': {
                        'duration_minutes': 30,
                        'audio_files': [
                            {
                                'id': 1,
                                'title': 'Patient Consultation',
                                'url': '/static/audio/consultation1.mp3',
                                'transcript': 'Doctor and patient consultation transcript...'
                            }
                        ],
                        'questions': [
                            {
                                'id': 1,
                                'question': 'What was the patient\'s main complaint?',
                                'type': 'multiple_choice',
                                'options': ['Headache', 'Fever', 'Cough', 'Fatigue'],
                                'correct_answer': 0
                            }
                        ]
                    },
                    'writing': {
                        'duration_minutes': 45,
                        'scenario': {
                            'patient_name': 'John Smith',
                            'age': '45',
                            'presenting_complaint': 'Chest pain',
                            'examination_findings': 'Elevated blood pressure',
                            'referral_to': 'Cardiology',
                            'task_instructions': 'Write a referral letter to the cardiologist'
                        },
                        'questions': [
                            {
                                'id': 1,
                                'question': 'Write a referral letter',
                                'type': 'essay',
                                'correct_answer': 'Sample referral letter format'
                            }
                        ]
                    },
                    'speaking': {
                        'duration_minutes': 20,
                        'role_plays': [
                            {
                                'id': 1,
                                'setting': 'Emergency Department',
                                'your_role': 'Nurse',
                                'patient': 'Elderly patient with chest pain',
                                'task': 'Explain the procedure and reassure the patient',
                                'time_limit': 5
                            }
                        ],
                        'questions': [
                            {
                                'id': 1,
                                'question': 'Record your role play response',
                                'type': 'speaking',
                                'correct_answer': 'Evaluation based on communication skills'
                            }
                        ]
                    }
                }
            }
        },
        {
            'id': 104,
            'title': 'OET Reading Mock Test',
            'section': 'Reading',
            'duration_minutes': 45,
            'description': 'Focused reading comprehension test',
            'is_mock_test': True,
            'is_premium': False,
            'content': {
                'sections': {
                    'reading': {
                        'duration_minutes': 45,
                        'passages': [
                            {
                                'id': 1,
                                'title': 'Medical Research Study',
                                'content': 'Recent research findings in healthcare...'
                            }
                        ],
                        'questions': [
                            {
                                'id': 1,
                                'question': 'What was the main conclusion of the study?',
                                'type': 'multiple_choice',
                                'options': ['Improved outcomes', 'Reduced costs', 'Better efficiency', 'Enhanced safety'],
                                'correct_answer': 0
                            }
                        ]
                    }
                }
            }
        },
        {
            'id': 105,
            'title': 'OET Listening Mock Test',
            'section': 'Listening',
            'duration_minutes': 30,
            'description': 'Focused listening comprehension test',
            'is_mock_test': True,
            'is_premium': False,
            'content': {
                'sections': {
                    'listening': {
                        'duration_minutes': 30,
                        'audio_files': [
                            {
                                'id': 1,
                                'title': 'Ward Round Discussion',
                                'url': '/static/audio/ward_round.mp3',
                                'transcript': 'Medical team discussion transcript...'
                            }
                        ],
                        'questions': [
                            {
                                'id': 1,
                                'question': 'What was discussed about the patient\'s medication?',
                                'type': 'multiple_choice',
                                'options': ['Increase dosage', 'Change medication', 'Continue current', 'Stop treatment'],
                                'correct_answer': 1
                            }
                        ]
                    }
                }
            }
        }
    ])

def get_all_tests():
    """Get all tests (both practice and mock tests) combined"""
    practice_tests = get_practice_tests()
    mock_tests = get_full_mock_tests()
    
    # Mark test types for easier identification
    for test in practice_tests:
        test['test_type'] = 'practice'
    
    for test in mock_tests:
        test['test_type'] = 'mock'
    
    return practice_tests + mock_tests

def get_test_by_id(test_id):
    # Check practice tests first
    practice_tests = get_practice_tests()
    for test in practice_tests:
        if test['id'] == test_id:
            test['test_type'] = 'practice'
            return test
    # Check full mock tests
    mock_tests = get_full_mock_tests()
    for test in mock_tests:
        if test['id'] == test_id:
            test['test_type'] = 'mock'
            return test
    return None

# Test results (practice)
def get_test_results():
    return load_json_file(TEST_RESULTS_FILE, [])

def save_test_results(results):
    save_json_file(TEST_RESULTS_FILE, results)

def get_user_test_results(user_id):
    results = get_test_results()
    user_results = []
    for result in results:
        if result.get('user_id') == user_id:
            # Try to get test from new system first
            from test_data_manager import test_manager
            test = test_manager.get_complete_test(result.get('test_id'), is_mock=False)
            if not test:
                # Fall back to old system
                test = get_test_by_id(result.get('test_id'))
            
            if test:
                r = result.copy()
                r['practice_test'] = {'title': test.get('title'), 'section': {'name': test.get('section')}}
                user_results.append(r)
    # sort by completed_at if present, else by id desc
    def keyfn(x):
        return x.get('completed_at', '') or ''
    return sorted(user_results, key=keyfn, reverse=True)

def save_test_result(user_id, test_id, score_percentage, time_taken_minutes, answers):
    results = get_test_results()
    result_id = get_next_id(results)
    result = {
        'id': result_id,
        'user_id': user_id,
        'test_id': test_id,
        'score_percentage': score_percentage,
        'time_taken_minutes': time_taken_minutes,
        'answers': answers,
        'completed_at': datetime.now().strftime('%Y-%m-%d %H:%M')
    }
    results.append(result)
    save_test_results(results)
    return result_id

# Mock test results (anonymous allowed)
def get_mock_test_results():
    return load_json_file(MOCK_TEST_RESULTS_FILE, [])

def save_mock_test_results(results):
    save_json_file(MOCK_TEST_RESULTS_FILE, results)

def get_user_mock_test_results(user_id=None):
    # If user_id provided, return that user's mock results; otherwise return all results.
    results = get_mock_test_results()
    if user_id is None:
        return results
    return [r for r in results if r.get('user_id') == user_id]

def get_mock_result_by_id(result_id):
    results = get_mock_test_results()
    for r in results:
        if r['id'] == result_id:
            return r
    return None

def save_mock_test_result(user_id, test_id, score_percentage, time_taken_minutes, answers):
    results = get_mock_test_results()
    result_id = get_next_id(results)
    result = {
        'id': result_id,
        'user_id': user_id,
        'test_id': test_id,
        'score_percentage': score_percentage,
        'time_taken_minutes': time_taken_minutes,
        'answers': answers,
        'completed_at': datetime.now().strftime('%Y-%m-%d %H:%M')
    }
    results.append(result)
    save_mock_test_results(results)
    return result_id

# Vocabulary management
def get_vocabulary_words(specialty=None):
    words = load_json_file(VOCABULARY_FILE, [])
    if specialty:
        return [word for word in words if word.get('specialty', '').lower() == specialty.lower()]
    return words

def get_user_vocabulary_progress(user_id):
    progress_data = load_json_file(VOCABULARY_PROGRESS_FILE, {})
    return progress_data.get(str(user_id), {'learned_words': []})

def save_vocabulary_progress(progress_data):
    save_json_file(VOCABULARY_PROGRESS_FILE, progress_data)

def mark_word_as_learned(user_id, word_id):
    progress_data = load_json_file(VOCABULARY_PROGRESS_FILE, {})
    user_progress = progress_data.get(str(user_id), {'learned_words': []})
    if word_id not in user_progress['learned_words']:
        user_progress['learned_words'].append(word_id)
        progress_data[str(user_id)] = user_progress
        save_vocabulary_progress(progress_data)
        return True
    return False

def test_vocabulary_word(word):
    vocabulary = get_vocabulary_words()
    for vocab_word in vocabulary:
        if vocab_word.get('word', '').lower() == word.lower():
            return {
                'correct': True,
                'word': vocab_word['word'],
                'definition': vocab_word.get('definition', ''),
                'specialty': vocab_word.get('specialty', '')
            }
    return {'correct': False, 'message': f'"{word}" is not found in our medical vocabulary database.'}


# Chat functionality
CHAT_MESSAGES_FILE = os.path.join(DATA_DIR, 'chat_messages.json')

def get_chat_messages():
    return load_json_file(CHAT_MESSAGES_FILE, [])

def save_chat_messages(messages):
    save_json_file(CHAT_MESSAGES_FILE, messages)

def add_chat_message(user_id, username, message, is_admin_reply=False):
    messages = get_chat_messages()
    new_message = {
        'id': len(messages) + 1,
        'user_id': user_id,
        'username': username,
        'message': message,
        'timestamp': datetime.now().isoformat(),
        'is_admin_reply': is_admin_reply,
        'is_read': False
    }
    messages.append(new_message)
    save_chat_messages(messages)
    return new_message

def get_user_chat_messages(user_id):
    messages = get_chat_messages()
    return [msg for msg in messages if msg['user_id'] == user_id]

def get_all_chat_messages():
    return get_chat_messages()

def mark_message_as_read(message_id):
    messages = get_chat_messages()
    for msg in messages:
        if msg['id'] == message_id:
            msg['is_read'] = True
            break
    save_chat_messages(messages)

def update_test_content(test_id, updated_test):
    """Update test content - works for both practice and mock tests"""
    try:
        # Try to update in practice tests first
        practice_tests = get_practice_tests()
        for i, test in enumerate(practice_tests):
            if test['id'] == test_id:
                practice_tests[i] = updated_test
                save_json_file(PRACTICE_TESTS_FILE, practice_tests)
                return True
        
        # Try to update in mock tests
        mock_tests = get_full_mock_tests()
        for i, test in enumerate(mock_tests):
            if test['id'] == test_id:
                mock_tests[i] = updated_test
                save_json_file(FULL_MOCK_TESTS_FILE, mock_tests)
                return True
        
        return False
    except Exception as e:
        print(f"Error updating test content: {e}")
        return False


def add_vocabulary_word(word, definition, specialty):
    """Add a new vocabulary word"""
    try:
        words = get_vocabulary_words()
        word_id = get_next_id(words)
        
        new_word = {
            'id': word_id,
            'word': word,
            'definition': definition,
            'specialty': specialty if specialty else 'General'
        }
        
        words.append(new_word)
        save_json_file(VOCABULARY_FILE, words)
        return True
    except Exception as e:
        print(f"Error adding vocabulary word: {e}")
        return False


def get_vocabulary_word_by_id(word_id):
    """Get a vocabulary word by ID"""
    words = get_vocabulary_words()
    for word in words:
        if word.get('id') == word_id:
            return word
    return None


def update_vocabulary_word(word_id, word, definition, specialty):
    """Update an existing vocabulary word"""
    try:
        words = get_vocabulary_words()
        
        for i, w in enumerate(words):
            if w.get('id') == word_id:
                words[i] = {
                    'id': word_id,
                    'word': word,
                    'definition': definition,
                    'specialty': specialty if specialty else 'General'
                }
                save_json_file(VOCABULARY_FILE, words)
                return True
        
        return False
    except Exception as e:
        print(f"Error updating vocabulary word: {e}")
        return False


def delete_vocabulary_word(word_id):
    """Delete a vocabulary word"""
    try:
        words = get_vocabulary_words()
        words = [w for w in words if w.get('id') != word_id]
        save_json_file(VOCABULARY_FILE, words)
        return True
    except Exception as e:
        print(f"Error deleting vocabulary word: {e}")
        return False


def create_new_test(title, section, duration, description, is_mock, is_premium):
    """Create a new test"""
    try:
        if is_mock:
            tests = get_full_mock_tests()
            test_id = get_next_id(tests)
            
            new_test = {
                'id': test_id,
                'title': title,
                'section': section,
                'duration_minutes': duration,
                'description': description,
                'is_mock_test': True,
                'is_premium': is_premium,
                'content': {
                    'sections': {}
                }
            }
            
            tests.append(new_test)
            save_json_file(FULL_MOCK_TESTS_FILE, tests)
            return test_id
        else:
            # Create practice test
            tests = get_practice_tests()
            test_id = get_next_id(tests)
            
            new_test = {
                'id': test_id,
                'title': title,
                'section': section,
                'duration_minutes': duration,
                'description': description,
                'is_mock_test': False,
                'is_premium': is_premium,
                'content': {
                    'sections': {}
                }
            }
            
            tests.append(new_test)
            save_json_file(PRACTICE_TESTS_FILE, tests)
            return test_id
    except Exception as e:
        print(f"Error creating test: {e}")
        return None


def delete_test(test_id):
    """Delete a test"""
    try:
        # Try to delete from practice tests first
        practice_tests = get_practice_tests()
        original_length = len(practice_tests)
        practice_tests = [t for t in practice_tests if t['id'] != test_id]
        
        if len(practice_tests) < original_length:
            save_json_file(PRACTICE_TESTS_FILE, practice_tests)
            return True
        
        # Try to delete from mock tests
        mock_tests = get_full_mock_tests()
        original_length = len(mock_tests)
        mock_tests = [t for t in mock_tests if t['id'] != test_id]
        
        if len(mock_tests) < original_length:
            save_json_file(FULL_MOCK_TESTS_FILE, mock_tests)
            return True
        
        return False
    except Exception as e:
        print(f"Error deleting test: {e}")
        return False


# Job management functions
def get_jobs():
    """Get all jobs"""
    return load_json_file(JOBS_FILE, [])


def save_jobs(jobs):
    """Save jobs to file"""
    save_json_file(JOBS_FILE, jobs)


def get_job_by_id(job_id):
    """Get a job by ID"""
    jobs = get_jobs()
    for job in jobs:
        if job.get('id') == job_id:
            return job
    return None


def create_job(title, company, location, job_type, salary_range, description, requirements, contact_email):
    """Create a new job posting"""
    try:
        jobs = get_jobs()
        job_id = get_next_id(jobs)
        
        new_job = {
            'id': job_id,
            'title': title,
            'company': company,
            'location': location,
            'job_type': job_type,
            'salary_range': salary_range,
            'description': description,
            'requirements': requirements,
            'contact_email': contact_email,
            'posted_date': datetime.now().strftime('%Y-%m-%d'),
            'is_active': True
        }
        
        jobs.append(new_job)
        save_jobs(jobs)
        return job_id
    except Exception as e:
        print(f"Error creating job: {e}")
        return None


def update_job(job_id, title, company, location, job_type, salary_range, description, requirements, contact_email, is_active=True):
    """Update an existing job"""
    try:
        jobs = get_jobs()
        
        for i, job in enumerate(jobs):
            if job.get('id') == job_id:
                jobs[i] = {
                    'id': job_id,
                    'title': title,
                    'company': company,
                    'location': location,
                    'job_type': job_type,
                    'salary_range': salary_range,
                    'description': description,
                    'requirements': requirements,
                    'contact_email': contact_email,
                    'posted_date': job.get('posted_date', datetime.now().strftime('%Y-%m-%d')),
                    'is_active': is_active
                }
                save_jobs(jobs)
                return True
        
        return False
    except Exception as e:
        print(f"Error updating job: {e}")
        return False


def delete_job(job_id):
    """Delete a job"""
    try:
        jobs = get_jobs()
        jobs = [j for j in jobs if j.get('id') != job_id]
        save_jobs(jobs)
        return True
    except Exception as e:
        print(f"Error deleting job: {e}")
        return False


def get_active_jobs():
    """Get only active jobs"""
    jobs = get_jobs()
    return [job for job in jobs if job.get('is_active', True)]