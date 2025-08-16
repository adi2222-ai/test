# OET Preparation Platform

## Overview

An educational web platform designed for medical professionals preparing for the Occupational English Test (OET). The platform provides comprehensive study resources including practice tests for all four OET sections (Listening, Reading, Writing, Speaking), medical vocabulary learning with progress tracking, and subscription-based access to premium content. Built as a complete learning management system with user authentication, progress analytics, and responsive design optimized for medical professionals studying for English proficiency certification.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Web Framework Architecture
- **Flask Application**: Modular Python web framework with separation of concerns across multiple files (app.py, routes.py, forms.py)
- **Template Engine**: Jinja2 templating system with Bootstrap 5 for responsive, mobile-first UI design
- **Static Asset Management**: Organized CSS and JavaScript files with custom medical-themed styling and Font Awesome icons
- **Form Handling**: Flask-WTF integration for secure form processing, validation, and CSRF protection

### Authentication & Session Management
- **Flask-Login**: Session-based user authentication with secure password hashing using Werkzeug
- **User Model**: Custom User class implementing Flask-Login UserMixin for authentication state management
- **Role-Based Access**: Two-tier permission system distinguishing regular users from administrators
- **Session Security**: Environment-configurable secret keys with proxy fix middleware for deployment

### Data Storage Strategy
- **File-Based Architecture**: Complete JSON file storage system eliminating database dependencies for maximum portability
- **Data Manager Module**: Centralized data_manager.py handles all CRUD operations with atomic file operations
- **Storage Structure**: Organized data directory with separate JSON files for users, vocabulary, test results, practice tests, and progress tracking
- **Thread Safety**: Proper file locking and error handling for concurrent access scenarios

### Core Educational Components
- **Assessment Framework**: Comprehensive test system supporting all four OET sections with timed examinations and automatic scoring
- **Vocabulary System**: Medical terminology database with specialty categorization, progress tracking, and interactive learning features
- **Progress Analytics**: Detailed performance tracking including test scores, vocabulary mastery, and learning analytics
- **Content Management**: Structured storage for practice tests, full mock examinations, and educational resources

### Subscription & Access Control
- **Tiered Access Model**: Free tier with basic practice tests and premium subscription for full mock tests and advanced features
- **Subscription Validation**: Server-side subscription status checking with expiration date management
- **Content Gating**: Dynamic access control based on subscription status and user authentication level

### Frontend Architecture
- **Responsive Design**: Bootstrap 5 framework with custom CSS for medical professional aesthetics
- **Glass Morphism UI**: Modern design language with backdrop filters and translucent elements
- **Progressive Enhancement**: JavaScript-enhanced interactions with fallback functionality for accessibility
- **Mobile Optimization**: Touch-friendly interface with responsive breakpoints for various device sizes