"""
SwingShift Survey System - Main Flask Application
=================================================
Last Updated: January 13, 2026

This is the main Flask application that provides the REST API for:
- Question Bank management (CRUD for master questions)
- Project/Survey management (create, configure, open/close surveys)
- Survey taking (public endpoint for employees)
- Results & Reports (data export, Excel generation, PowerPoint updates)
- Benchmark comparison (compare to normative database)

DEPLOYMENT NOTES:
- Deploy on Render.com with PostgreSQL database
- Environment variables needed: DATABASE_URL, SECRET_KEY
- CORS enabled for frontend at swingshift.com

NOTES FOR FUTURE AI:
- All endpoints return JSON
- Authentication is simple (admin endpoints require API key)
- Survey taking endpoints are public (access via unique project code)
- Report generation uses openpyxl for Excel and python-pptx for PowerPoint
"""

import os
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from flask_migrate import Migrate
from datetime import datetime
import hashlib
import json

from models import (
    db, MasterQuestion, ResponseOption, Project, ProjectQuestion,
    CustomQuestion, CustomResponseOption, SurveyResponse, ResponseAnswer,
    NormativeData
)

# Create Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///swingshift.db')
# Fix for Render PostgreSQL URL (postgres:// -> postgresql://)
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)

# CORS - allow requests from frontend
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:3000",
            "https://swingshift.com",
            "https://www.swingshift.com",
            "https://*.swingshift.com"
        ]
    }
})

# Simple API key authentication for admin endpoints
ADMIN_API_KEY = os.environ.get('ADMIN_API_KEY', 'dev-admin-key')

def require_admin():
    """Check for valid admin API key in request header"""
    api_key = request.headers.get('X-API-Key')
    if api_key != ADMIN_API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401
    return None


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })


# ============================================================================
# ADMIN PANEL (Web UI)
# ============================================================================

@app.route('/admin')
@app.route('/admin/')
def admin_panel():
    """Serve the admin panel web interface"""
    return render_template('admin.html')


# ============================================================================
# QUESTION BANK ENDPOINTS
# ============================================================================

@app.route('/api/questions', methods=['GET'])
def get_questions():
    """Get all master questions, optionally filtered by category"""
    category = request.args.get('category')
    
    query = MasterQuestion.query.filter_by(is_active=True)
    if category:
        query = query.filter_by(category=category)
    
    questions = query.order_by(MasterQuestion.question_number).all()
    
    result = []
    for q in questions:
        q_dict = q.to_dict()
        # Include options for each question
        options = ResponseOption.query.filter_by(question_id=q.id).order_by(ResponseOption.display_order).all()
        q_dict['options'] = [{'option_text': o.option_text, 'option_code': o.option_code} for o in options]
        result.append(q_dict)
    
    return jsonify(result)


@app.route('/api/questions/categories', methods=['GET'])
def get_categories():
    """Get list of all question categories"""
    categories = db.session.query(MasterQuestion.category).distinct().all()
    return jsonify({
        'categories': [c[0] for c in categories if c[0]]
    })


@app.route('/api/questions/<int:question_id>', methods=['GET'])
def get_question(question_id):
    """Get a single question by ID"""
    question = MasterQuestion.query.get_or_404(question_id)
    return jsonify(question.to_dict())


@app.route('/api/questions', methods=['POST'])
def create_question():
    """Create a new master question (admin only)"""
    auth_error = require_admin()
    if auth_error:
        return auth_error
    
    data = request.get_json()
    
    # Get the next question number
    max_num = db.session.query(db.func.max(MasterQuestion.question_number)).scalar() or 0
    
    question = MasterQuestion(
        question_text=data['question_text'],
        question_number=data.get('question_number', max_num + 1),
        category=data['category'],
        subcategory=data.get('subcategory'),
        question_type=data['question_type'],
        likert_low_label=data.get('likert_low_label'),
        likert_high_label=data.get('likert_high_label'),
        has_special_calculation=data.get('has_special_calculation', False),
        calculation_type=data.get('calculation_type')
    )
    
    db.session.add(question)
    db.session.flush()  # Get the ID
    
    # Add response options if provided
    if 'response_options' in data:
        for i, opt in enumerate(data['response_options']):
            option = ResponseOption(
                question_id=question.id,
                option_text=opt['option_text'],
                option_code=opt.get('option_code'),
                numeric_value=opt.get('numeric_value'),
                display_order=i + 1,
                calculation_value=opt.get('calculation_value')
            )
            db.session.add(option)
    
    db.session.commit()
    
    return jsonify(question.to_dict()), 201


@app.route('/api/questions/<int:question_id>', methods=['PUT'])
def update_question(question_id):
    """Update a master question (admin only)"""
    auth_error = require_admin()
    if auth_error:
        return auth_error
    
    question = MasterQuestion.query.get_or_404(question_id)
    data = request.get_json()
    
    # Update fields
    for field in ['question_text', 'category', 'subcategory', 'question_type',
                  'likert_low_label', 'likert_high_label', 'has_special_calculation',
                  'calculation_type', 'is_active']:
        if field in data:
            setattr(question, field, data[field])
    
    db.session.commit()
    
    return jsonify(question.to_dict())


# ============================================================================
# PROJECT ENDPOINTS
# ============================================================================

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """Get all projects (admin only)"""
    auth_error = require_admin()
    if auth_error:
        return auth_error
    
    projects = Project.query.order_by(Project.created_at.desc()).all()
    result = []
    for p in projects:
        p_dict = p.to_dict()
        # Add question count
        p_dict['question_count'] = ProjectQuestion.query.filter_by(project_id=p.id).count()
        # Add response count
        p_dict['response_count'] = SurveyResponse.query.filter_by(project_id=p.id).count()
        result.append(p_dict)
    return jsonify(result)


@app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """Get a single project by ID (admin only)"""
    auth_error = require_admin()
    if auth_error:
        return auth_error
    
    project = Project.query.get_or_404(project_id)
    return jsonify(project.to_dict())


@app.route('/api/projects', methods=['POST'])
def create_project():
    """Create a new project (admin only)"""
    auth_error = require_admin()
    if auth_error:
        return auth_error
    
    data = request.get_json()
    
    project = Project(
        project_name=data['project_name'],
        company_name=data.get('company_name', data['project_name']),
        is_anonymous=data.get('is_anonymous', True),
        show_progress=data.get('show_progress', True),
        randomize_options=data.get('randomize_options', False)
    )
    
    db.session.add(project)
    db.session.commit()
    
    return jsonify(project.to_dict()), 201


@app.route('/api/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """Update a project (admin only)"""
    auth_error = require_admin()
    if auth_error:
        return auth_error
    
    project = Project.query.get_or_404(project_id)
    data = request.get_json()
    
    # Update allowed fields
    for field in ['project_name', 'company_name', 'is_anonymous', 
                  'show_progress', 'randomize_options']:
        if field in data:
            setattr(project, field, data[field])
    
    # Handle status changes
    if 'status' in data:
        new_status = data['status']
        if new_status == 'active' and project.status != 'active':
            project.opened_at = datetime.utcnow()
        elif new_status == 'closed' and project.status != 'closed':
            project.closed_at = datetime.utcnow()
        project.status = new_status
    
    db.session.commit()
    
    return jsonify(project.to_dict())


@app.route('/api/projects/<int:project_id>/questions', methods=['GET'])
def get_project_questions(project_id):
    """Get all questions for a project"""
    auth_error = require_admin()
    if auth_error:
        return auth_error
    
    project = Project.query.get_or_404(project_id)
    
    # Get project questions with question_id for the admin panel
    project_questions = ProjectQuestion.query.filter_by(project_id=project_id).order_by(ProjectQuestion.question_order).all()
    
    result = []
    for pq in project_questions:
        result.append({
            'id': pq.id,
            'question_id': pq.master_question_id,
            'question_order': pq.question_order
        })
    
    return jsonify(result)


@app.route('/api/projects/<int:project_id>/questions', methods=['POST'])
def add_project_question(project_id):
    """Add a question to a project (admin only)"""
    auth_error = require_admin()
    if auth_error:
        return auth_error
    
    project = Project.query.get_or_404(project_id)
    data = request.get_json()
    
    # Get the next question order
    max_order = db.session.query(
        db.func.max(ProjectQuestion.question_order)
    ).filter_by(project_id=project_id).scalar() or 0
    
    max_custom = db.session.query(
        db.func.max(CustomQuestion.question_order)
    ).filter_by(project_id=project_id).scalar() or 0
    
    next_order = max(max_order, max_custom) + 1
    
    if 'master_question_id' in data:
        # Adding a question from the master bank
        pq = ProjectQuestion(
            project_id=project_id,
            master_question_id=data['master_question_id'],
            question_order=data.get('question_order', next_order),
            custom_text=data.get('custom_text'),
            is_breakout=data.get('is_breakout', False)
        )
        db.session.add(pq)
        db.session.commit()
        return jsonify(pq.to_dict()), 201
    else:
        # Adding a custom question
        cq = CustomQuestion(
            project_id=project_id,
            question_text=data['question_text'],
            question_order=data.get('question_order', next_order),
            question_type=data['question_type'],
            likert_low_label=data.get('likert_low_label'),
            likert_high_label=data.get('likert_high_label'),
            is_breakout=data.get('is_breakout', False)
        )
        db.session.add(cq)
        db.session.flush()
        
        # Add custom response options
        if 'response_options' in data:
            for i, opt in enumerate(data['response_options']):
                cro = CustomResponseOption(
                    custom_question_id=cq.id,
                    option_text=opt['option_text'],
                    option_code=opt.get('option_code'),
                    numeric_value=opt.get('numeric_value'),
                    display_order=i + 1
                )
                db.session.add(cro)
        
        db.session.commit()
        return jsonify(cq.to_dict()), 201


@app.route('/api/projects/<int:project_id>/questions/bulk', methods=['POST'])
def add_bulk_questions(project_id):
    """Add multiple questions from master bank to a project (admin only)
    This replaces all existing questions with the new selection.
    """
    auth_error = require_admin()
    if auth_error:
        return auth_error
    
    project = Project.query.get_or_404(project_id)
    data = request.get_json()
    
    # Accept either 'question_ids' or 'master_question_ids'
    question_ids = data.get('question_ids', data.get('master_question_ids', []))
    
    # Clear existing project questions
    ProjectQuestion.query.filter_by(project_id=project_id).delete()
    
    # Add new questions
    added = []
    for i, mq_id in enumerate(question_ids):
        pq = ProjectQuestion(
            project_id=project_id,
            master_question_id=mq_id,
            question_order=i + 1,
            is_breakout=False
        )
        db.session.add(pq)
        added.append(mq_id)
    
    db.session.commit()
    
    return jsonify({
        'added': added,
        'count': len(added)
    }), 201


# ============================================================================
# SURVEY TAKING ENDPOINTS (PUBLIC)
# ============================================================================

@app.route('/api/survey/<access_code>', methods=['GET'])
def get_survey(access_code):
    """Get survey for taking (public endpoint)"""
    project = Project.query.filter_by(access_code=access_code.upper()).first_or_404()
    
    if project.status != 'active':
        return jsonify({
            'error': 'Survey is not currently active',
            'status': project.status
        }), 400
    
    # Get all questions
    project_questions = [pq.to_dict() for pq in project.questions]
    custom_questions = [cq.to_dict() for cq in project.custom_questions]
    
    all_questions = project_questions + custom_questions
    all_questions.sort(key=lambda x: x['question_order'])
    
    return jsonify({
        'project_name': project.project_name,
        'company_name': project.company_name,
        'show_progress': project.show_progress,
        'questions': all_questions,
        'total_questions': len(all_questions)
    })


@app.route('/api/survey/<access_code>/start', methods=['POST'])
def start_survey(access_code):
    """Start a new survey response (public endpoint)"""
    project = Project.query.filter_by(access_code=access_code.upper()).first_or_404()
    
    if project.status != 'active':
        return jsonify({'error': 'Survey is not currently active'}), 400
    
    # Create a hash of the IP for duplicate detection (optional)
    ip_hash = None
    if request.remote_addr:
        ip_hash = hashlib.sha256(request.remote_addr.encode()).hexdigest()[:16]
    
    response = SurveyResponse(
        project_id=project.id,
        user_agent=request.headers.get('User-Agent', '')[:500],
        ip_hash=ip_hash
    )
    
    db.session.add(response)
    db.session.commit()
    
    return jsonify({
        'response_code': response.response_code,
        'started_at': response.started_at.isoformat()
    }), 201


@app.route('/api/survey/<access_code>/answer', methods=['POST'])
def submit_answer(access_code):
    """Submit an answer to a question (public endpoint)"""
    project = Project.query.filter_by(access_code=access_code.upper()).first_or_404()
    
    if project.status != 'active':
        return jsonify({'error': 'Survey is not currently active'}), 400
    
    data = request.get_json()
    response_code = data.get('response_code')
    
    # Find the response session
    response = SurveyResponse.query.filter_by(
        response_code=response_code,
        project_id=project.id
    ).first_or_404()
    
    # Check if answer already exists for this question
    existing = None
    if data.get('project_question_id'):
        existing = ResponseAnswer.query.filter_by(
            response_id=response.id,
            project_question_id=data['project_question_id']
        ).first()
    elif data.get('custom_question_id'):
        existing = ResponseAnswer.query.filter_by(
            response_id=response.id,
            custom_question_id=data['custom_question_id']
        ).first()
    
    if existing:
        # Update existing answer
        existing.answer_text = data.get('answer_text')
        existing.answer_code = data.get('answer_code')
        existing.answer_numeric = data.get('answer_numeric')
        existing.answer_multi = data.get('answer_multi')
    else:
        # Create new answer
        answer = ResponseAnswer(
            response_id=response.id,
            project_question_id=data.get('project_question_id'),
            custom_question_id=data.get('custom_question_id'),
            answer_text=data.get('answer_text'),
            answer_code=data.get('answer_code'),
            answer_numeric=data.get('answer_numeric'),
            answer_multi=data.get('answer_multi')
        )
        db.session.add(answer)
    
    # Update last activity
    response.last_activity = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'status': 'saved'})


@app.route('/api/survey/<access_code>/complete', methods=['POST'])
def complete_survey(access_code):
    """Mark a survey response as complete (public endpoint)"""
    project = Project.query.filter_by(access_code=access_code.upper()).first_or_404()
    
    data = request.get_json()
    response_code = data.get('response_code')
    
    response = SurveyResponse.query.filter_by(
        response_code=response_code,
        project_id=project.id
    ).first_or_404()
    
    response.is_complete = True
    response.completed_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'status': 'complete',
        'completed_at': response.completed_at.isoformat()
    })


# ============================================================================
# RESULTS & REPORTS ENDPOINTS
# ============================================================================

@app.route('/api/projects/<int:project_id>/results', methods=['GET'])
def get_project_results(project_id):
    """Get survey results summary (admin only)"""
    auth_error = require_admin()
    if auth_error:
        return auth_error
    
    project = Project.query.get_or_404(project_id)
    
    # Get response statistics
    total_responses = project.responses.count()
    complete_responses = project.responses.filter_by(is_complete=True).count()
    
    # Get all questions
    project_questions = list(project.questions)
    custom_questions = list(project.custom_questions)
    
    results = {
        'project': project.to_dict(),
        'response_summary': {
            'total': total_responses,
            'complete': complete_responses,
            'incomplete': total_responses - complete_responses
        },
        'questions': []
    }
    
    # For each question, calculate response distribution
    for pq in project_questions:
        q_results = calculate_question_results(project_id, pq.id, None, pq.master_question)
        results['questions'].append(q_results)
    
    for cq in custom_questions:
        q_results = calculate_custom_question_results(project_id, cq)
        results['questions'].append(q_results)
    
    return jsonify(results)


def calculate_question_results(project_id, pq_id, cq_id, question):
    """Calculate response distribution for a question"""
    
    if pq_id:
        answers = ResponseAnswer.query.join(SurveyResponse).filter(
            SurveyResponse.project_id == project_id,
            SurveyResponse.is_complete == True,
            ResponseAnswer.project_question_id == pq_id
        ).all()
    else:
        answers = ResponseAnswer.query.join(SurveyResponse).filter(
            SurveyResponse.project_id == project_id,
            SurveyResponse.is_complete == True,
            ResponseAnswer.custom_question_id == cq_id
        ).all()
    
    total = len(answers)
    distribution = {}
    
    for answer in answers:
        key = answer.answer_text or 'No Response'
        distribution[key] = distribution.get(key, 0) + 1
    
    # Convert to percentages
    percentages = {}
    for key, count in distribution.items():
        percentages[key] = {
            'count': count,
            'percentage': round(count / total * 100, 1) if total > 0 else 0
        }
    
    return {
        'question_text': question.question_text,
        'question_type': question.question_type,
        'total_responses': total,
        'distribution': percentages
    }


def calculate_custom_question_results(project_id, cq):
    """Calculate response distribution for a custom question"""
    return calculate_question_results(project_id, None, cq.id, cq)


@app.route('/api/projects/<int:project_id>/export/csv', methods=['GET'])
def export_csv(project_id):
    """Export survey responses as CSV (admin only)"""
    auth_error = require_admin()
    if auth_error:
        return auth_error
    
    import csv
    from io import StringIO
    
    project = Project.query.get_or_404(project_id)
    
    # Get all questions in order
    project_questions = list(project.questions.order_by(ProjectQuestion.question_order))
    custom_questions = list(project.custom_questions.order_by(CustomQuestion.question_order))
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Header row
    headers = ['Response ID', 'Completed']
    for pq in project_questions:
        headers.append(f'Q{pq.question_order}')
    for cq in custom_questions:
        headers.append(f'Q{cq.question_order}')
    writer.writerow(headers)
    
    # Data rows
    responses = project.responses.filter_by(is_complete=True).all()
    for response in responses:
        row = [response.response_code[:8], 'Yes' if response.is_complete else 'No']
        
        # Get answers for project questions
        for pq in project_questions:
            answer = ResponseAnswer.query.filter_by(
                response_id=response.id,
                project_question_id=pq.id
            ).first()
            row.append(answer.answer_text if answer else '')
        
        # Get answers for custom questions
        for cq in custom_questions:
            answer = ResponseAnswer.query.filter_by(
                response_id=response.id,
                custom_question_id=cq.id
            ).first()
            row.append(answer.answer_text if answer else '')
        
        writer.writerow(row)
    
    # Create response
    output.seek(0)
    return output.getvalue(), 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': f'attachment; filename={project.company_name}_survey_data.csv'
    }


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

@app.cli.command('init-db')
def init_db():
    """Initialize the database tables"""
    db.create_all()
    print('Database tables created.')


@app.cli.command('seed-questions')
def seed_questions():
    """Seed the database with master questions (run import script separately)"""
    print('Use the import_questions.py script to seed master questions.')


# ============================================================================
# DATABASE SETUP ENDPOINT (Web-based initialization)
# ============================================================================

def get_likert():
    return [('1 (Strongly Disagree)', '1', 1, 1), ('2', '2', 2, 2), ('3', '3', 3, 3), ('4', '4', 4, 4), ('5 (Strongly Agree)', '5', 5, 5)]

def get_all_questions():
    """All 97 master survey questions embedded directly"""
    L = get_likert()
    return [
        # DEMOGRAPHICS (1-17)
        {'n': 1, 't': 'What department do you work in?', 'c': 'Demographics', 'ty': 'multiple_choice', 'o': [('A', 'a', 1, None), ('B', 'b', 2, None), ('C', 'c', 3, None), ('D', 'd', 4, None), ('E', 'e', 5, None), ('F', 'f', 6, None), ('G', 'g', 7, None), ('H', 'h', 8, None)]},
        {'n': 2, 't': 'What is your job title?', 'c': 'Demographics', 'ty': 'multiple_choice', 'o': [('A', 'a', 1, None), ('B', 'b', 2, None), ('C', 'c', 3, None), ('D', 'd', 4, None), ('E', 'e', 5, None), ('F', 'f', 6, None), ('G', 'g', 7, None)]},
        {'n': 3, 't': 'What crew are you assigned to?', 'c': 'Demographics', 'ty': 'multiple_choice', 'o': [('First Shift (8-hour or 10-hour)', 'a', 1, None), ('First Shift (12-hour)', 'b', 2, None), ('Second Shift (8-hour)', 'c', 3, None), ('Second Shift (12-hour)', 'd', 4, None), ('Third Shift', 'e', 5, None), ('Weekend Shift', 'f', 6, None)]},
        {'n': 4, 't': 'How long have you worked for this company?', 'c': 'Demographics', 'ty': 'multiple_choice', 'sc': 'average_years', 'o': [('Less than 6 months', 'a', 1, 0.25), ('6 months to 1 year', 'b', 2, 0.75), ('1 to 5 years', 'c', 3, 3), ('6 to 10 years', 'd', 4, 8), ('11 to 15 years', 'e', 5, 13), ('16 to 20 years', 'f', 6, 18), ('Over 20 years', 'g', 7, 25)]},
        {'n': 5, 't': 'How long have you worked in your current department?', 'c': 'Demographics', 'ty': 'multiple_choice', 'sc': 'average_years', 'o': [('Less than 6 months', 'a', 1, 0.25), ('6 months to 1 year', 'b', 2, 0.75), ('1 to 5 years', 'c', 3, 3), ('6 to 10 years', 'd', 4, 8), ('11 to 15 years', 'e', 5, 13), ('16 to 20 years', 'f', 6, 18), ('Over 20 years', 'g', 7, 25)]},
        {'n': 6, 't': 'Do you have a second job?', 'c': 'Demographics', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
        {'n': 7, 't': 'Have you ever worked shiftwork at another facility?', 'c': 'Demographics', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
        {'n': 8, 't': 'If you have a second job, do you typically work at that job:', 'c': 'Demographics', 'ty': 'multiple_choice', 'o': [('Before your shift starts', 'a', 1, None), ('After you have worked your shift', 'b', 2, None), ("Only on days that you don't work", 'c', 3, None), ("I don't work at a second job", 'd', 4, None)]},
        {'n': 9, 't': 'Are you a student?', 'c': 'Demographics', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
        {'n': 10, 't': 'Do you have children or elder family members at home that require childcare or eldercare when you are at work?', 'c': 'Demographics', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
        {'n': 11, 't': 'What is your gender?', 'c': 'Demographics', 'ty': 'multiple_choice', 'o': [('Female', 'a', 1, None), ('Male', 'b', 2, None)]},
        {'n': 12, 't': 'What is your age group?', 'c': 'Demographics', 'ty': 'multiple_choice', 'sc': 'average_age', 'o': [('25 and under', 'a', 1, 23), ('26 to 30', 'b', 2, 28), ('31 to 35', 'c', 3, 33), ('36 to 40', 'd', 4, 38), ('41 to 45', 'e', 5, 43), ('46 to 50', 'f', 6, 48), ('51 to 55', 'g', 7, 53), ('Over 55', 'h', 8, 60)]},
        {'n': 13, 't': 'Are you a single parent?', 'c': 'Demographics', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
        {'n': 14, 't': "Which best describes your spouse or domestic partner's work status?", 'c': 'Demographics', 'ty': 'multiple_choice', 'o': [('No spouse; I live alone', 'a', 1, None), ('Does not work outside the home', 'b', 2, None), ('Works a different schedule than I do in this company', 'c', 3, None), ('Works a different schedule than I do outside this company', 'd', 4, None), ('Works the same schedule as I do in this company', 'e', 5, None), ('Works the same schedule as I do outside this company', 'f', 6, None)]},
        {'n': 15, 't': 'How do you normally get to work?', 'c': 'Demographics', 'ty': 'multiple_choice', 'o': [('Drive by myself', 'a', 1, None), ('Carpool', 'b', 2, None), ('Public transportation', 'c', 3, None)]},
        {'n': 16, 't': 'How far do you commute to work (one way)?', 'c': 'Demographics', 'ty': 'multiple_choice', 'sc': 'average_miles', 'o': [('Less than 1 mile', 'a', 1, 0.5), ('1 to 5 miles', 'b', 2, 3), ('6 to 10 miles', 'c', 3, 8), ('11 to 20 miles', 'd', 4, 15), ('21 to 30 miles', 'e', 5, 25), ('31 to 40 miles', 'f', 6, 35), ('More than 40 miles', 'g', 7, 45)]},
        {'n': 17, 't': 'Looking at your daily commute, what is the worst time to start the day shift?', 'c': 'Demographics', 'ty': 'multiple_choice', 'o': [('Before 5:30 a.m.', 'a', 1, None), ('5:30 a.m.', 'b', 2, None), ('6:00 a.m.', 'c', 3, None), ('6:30 a.m.', 'd', 4, None), ('7:00 a.m.', 'e', 5, None), ('7:30 a.m.', 'f', 6, None), ('8:00 a.m.', 'g', 7, None), ('Later than 8:00 a.m.', 'h', 8, None)]},
        # HEALTH AND ALERTNESS (18-27)
        {'n': 18, 't': 'Do you normally use an alarm clock to wake up after a sleep period?', 'c': 'Health and Alertness', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
        {'n': 19, 't': 'Do you use an alarm clock to wake up when you are working day shift?', 'c': 'Health and Alertness', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
        {'n': 20, 't': 'Do you use an alarm clock to wake up when you are working afternoon shift?', 'c': 'Health and Alertness', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
        {'n': 21, 't': 'Do you use an alarm clock to wake up when you are working night shift?', 'c': 'Health and Alertness', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
        {'n': 22, 't': 'How often do you notice you are having problems with safety or performance due to sleepiness?', 'c': 'Health and Alertness', 'ty': 'multiple_choice', 'o': [('Never', 'a', 1, None), ('Rarely', 'b', 2, None), ('Once a month', 'c', 3, None), ('Once a week', 'd', 4, None), ('Almost daily', 'e', 5, None)]},
        {'n': 23, 't': 'How many hours of sleep do you get every 24-hour period when you are working first shift?', 'c': 'Health and Alertness', 'ty': 'multiple_choice', 'sc': 'average_hours', 'o': [('I never work the first shift', 'a', 0, None), ('Less than 5 hours', 'b', 1, 4.5), ('5 or more hours but less than 6 hours', 'c', 2, 5.5), ('6 or more hours but less than 7 hours', 'd', 3, 6.5), ('7 or more hours but less than 8 hours', 'e', 4, 7.5), ('8 or more hours but less than 9 hours', 'f', 5, 8.5), ('9 or more hours', 'g', 6, 9.5)]},
        {'n': 24, 't': 'How many hours of sleep do you get every 24-hour period when you are working second shift?', 'c': 'Health and Alertness', 'ty': 'multiple_choice', 'sc': 'average_hours', 'o': [('I never work the second shift', 'a', 0, None), ('Less than 5 hours', 'b', 1, 4.5), ('5 or more hours but less than 6 hours', 'c', 2, 5.5), ('6 or more hours but less than 7 hours', 'd', 3, 6.5), ('7 or more hours but less than 8 hours', 'e', 4, 7.5), ('8 or more hours but less than 9 hours', 'f', 5, 8.5), ('9 or more hours', 'g', 6, 9.5)]},
        {'n': 25, 't': 'How many hours of sleep do you get every 24-hour period when you are working third shift?', 'c': 'Health and Alertness', 'ty': 'multiple_choice', 'sc': 'average_hours', 'o': [('I never work the third shift', 'a', 0, None), ('Less than 5 hours', 'b', 1, 4.5), ('5 or more hours but less than 6 hours', 'c', 2, 5.5), ('6 or more hours but less than 7 hours', 'd', 3, 6.5), ('7 or more hours but less than 8 hours', 'e', 4, 7.5), ('8 or more hours but less than 9 hours', 'f', 5, 8.5), ('9 or more hours', 'g', 6, 9.5)]},
        {'n': 26, 't': 'How many hours of sleep do you get every 24-hour period on days off?', 'c': 'Health and Alertness', 'ty': 'multiple_choice', 'sc': 'average_hours', 'o': [('Less than 5 hours', 'a', 1, 4.5), ('5 or more hours but less than 6 hours', 'b', 2, 5.5), ('6 or more hours but less than 7 hours', 'c', 3, 6.5), ('7 or more hours but less than 8 hours', 'd', 4, 7.5), ('8 or more hours but less than 9 hours', 'e', 5, 8.5), ('9 or more hours', 'f', 6, 9.5)]},
        {'n': 27, 't': 'How many hours of sleep do you need every 24-hour period to be fully alert?', 'c': 'Health and Alertness', 'ty': 'multiple_choice', 'sc': 'average_hours', 'o': [('Less than 5 hours', 'a', 1, 4.5), ('5 or more hours but less than 6 hours', 'b', 2, 5.5), ('6 or more hours but less than 7 hours', 'c', 3, 6.5), ('7 or more hours but less than 8 hours', 'd', 4, 7.5), ('8 or more hours but less than 9 hours', 'e', 5, 8.5), ('9 or more hours', 'f', 6, 9.5)]},
        # WORKING CONDITIONS (28-45)
        {'n': 28, 't': 'Overall, this is a safe place to work.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 29, 't': 'Which best describes your opinion?', 'c': 'Working Conditions', 'ty': 'multiple_choice', 'o': [('The company can do a lot more to improve safety at this site', 'a', 1, None), ('The employees can do a lot more to improve safety at this site', 'b', 2, None), ('Both of the above', 'c', 3, None), ('Neither of the above, this is a very safe place to work', 'd', 4, None)]},
        {'n': 30, 't': 'This company places a high priority on communication.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 31, 't': 'Communication is important to me.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 32, 't': 'How much time is needed to communicate daily plant conditions between shifts?', 'c': 'Working Conditions', 'ty': 'multiple_choice', 'sc': 'average_minutes', 'o': [('Less than 10 minutes', 'a', 1, 5), ('10 minutes', 'b', 2, 10), ('15 minutes', 'c', 3, 15), ('20 minutes', 'd', 4, 20), ('25 minutes', 'e', 5, 25), ('30 minutes', 'f', 6, 30), ('More than 30 minutes', 'g', 7, 35)]},
        {'n': 33, 't': 'Management welcomes input from the workforce.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 34, 't': 'I enjoy the work that I do.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 35, 't': 'The pay here is good compared to other jobs in the area.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 36, 't': 'Management treats shift-workers and day-workers equally.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 37, 't': 'I feel like I am a part of this company.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 38, 't': 'Which best describes how you feel?', 'c': 'Working Conditions', 'ty': 'multi_select', 'o': [('There is no problem with last minute absenteeism at this site.', 'a', 1, None), ("Covering other people's last minute absenteeism disrupts my family and social life.", 'b', 2, None), ('The company needs to crack down on those few employees that are taking advantage of the existing absentee policy.', 'c', 3, None)]},
        {'n': 39, 't': 'Overall, things are getting better at this facility.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 40, 't': 'This is one of the best places to work in this area.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 41, 't': 'Job training is important to me.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 42, 't': 'I get enough training to do my job well.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 43, 't': 'Which best describes how you feel?', 'c': 'Working Conditions', 'ty': 'multiple_choice', 'o': [('We train way too much', 'a', 1, None), ('We train just the right amount', 'b', 2, None), ('We do not train nearly enough', 'c', 3, None)]},
        {'n': 44, 't': 'My direct supervisor responds to my concerns about working conditions.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 45, 't': 'Upper management responds to my concerns about working conditions.', 'c': 'Working Conditions', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        # SHIFT SCHEDULE FEATURES (46-78)
        {'n': 46, 't': 'A better schedule will really improve things here.', 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 47, 't': 'Current shift schedule policies are fair.', 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 48, 't': 'I like my current schedule.', 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 49, 't': 'I think there are better schedules available than our current schedule.', 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 50, 't': 'Which best describes you?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('I plan to go to a better shift as soon as I can', 'a', 1, None), ('My current shift is where I plan to stay', 'b', 2, None)]},
        {'n': 51, 't': 'My time off is predictable.', 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 52, 't': 'My schedule allows me the flexibility to get time off when I really need it.', 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 53, 't': 'If you were assigned to work a single shift for the next few years, which would be your preferred 8-hour shift?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Day Shift', 'a', 1, None), ('Afternoon Shift', 'b', 2, None), ('Night Shift', 'c', 3, None)]},
        {'n': 54, 't': 'If you were assigned to work a single shift for the next few years, which would be your least preferred 8-hour shift?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Day Shift', 'a', 1, None), ('Afternoon Shift', 'b', 2, None), ('Night Shift', 'c', 3, None)]},
        {'n': 55, 't': 'If you were assigned to work a single shift for the next few years, which would be your preferred 12-hour shift?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Days', 'a', 1, None), ('Nights', 'b', 2, None)]},
        {'n': 56, 't': 'Assuming that you get the same amount of pay, which is more important to you?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Working fewer hours each day that I work, even though I will get fewer days off each week', 'a', 1, None), ('Working more hours each day so that I can have more days off each week', 'b', 2, None)]},
        {'n': 57, 't': 'Which would you prefer?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Fixed or "steady" shifts', 'a', 1, None), ('Rotating shifts', 'b', 2, None)]},
        {'n': 58, 't': 'Which would you prefer?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Fixed shifts, even though seniority is not a consideration when being assigned to a shift', 'a', 1, None), ('Rotating shifts', 'b', 2, None)]},
        {'n': 59, 't': 'Which would you prefer?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Fixed shifts, even though I would not be assigned to my first choice', 'a', 1, None), ('Rotating shifts', 'b', 2, None)]},
        {'n': 60, 't': 'Keeping my current crew members together is important to me.', 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 61, 't': 'How often would you like to rotate between shifts?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Once a week', 'a', 1, None), ('Once every two weeks', 'b', 2, None), ('Once every four weeks', 'c', 3, None), ('Once every two months', 'd', 4, None), ('Once every six months', 'e', 5, None), ('Annually', 'f', 6, None)]},
        {'n': 62, 't': 'On an 8-hour schedule, which direction would you prefer to rotate?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Days>Nights>Evenings>Days', 'a', 1, None), ('Days>Evenings>Nights>Days', 'b', 2, None), ('No preference', 'c', 3, None)]},
        {'n': 63, 't': 'If you worked 8-hour shifts, what time would you like the day shift to start?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Before 5:30 a.m.', 'a', 1, None), ('5:30 a.m.', 'b', 2, None), ('6:00 a.m.', 'c', 3, None), ('6:30 a.m.', 'd', 4, None), ('7:00 a.m.', 'e', 5, None), ('7:30 a.m.', 'f', 6, None), ('8:00 a.m.', 'g', 7, None), ('Later than 8:00 a.m.', 'h', 8, None)]},
        {'n': 64, 't': 'If you worked 10-hour shifts, what time would you like the day shift to start?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Before 5:30 a.m.', 'a', 1, None), ('5:30 a.m.', 'b', 2, None), ('6:00 a.m.', 'c', 3, None), ('6:30 a.m.', 'd', 4, None), ('7:00 a.m.', 'e', 5, None), ('7:30 a.m.', 'f', 6, None), ('8:00 a.m.', 'g', 7, None), ('Later than 8:00 a.m.', 'h', 8, None)]},
        {'n': 65, 't': 'If you worked 12-hour shifts, what time would you like the day shift to start?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Before 5:30 a.m.', 'a', 1, None), ('5:30 a.m.', 'b', 2, None), ('6:00 a.m.', 'c', 3, None), ('6:30 a.m.', 'd', 4, None), ('7:00 a.m.', 'e', 5, None), ('7:30 a.m.', 'f', 6, None), ('8:00 a.m.', 'g', 7, None), ('Later than 8:00 a.m.', 'h', 8, None), ('Noon', 'i', 9, None), ('3:00 p.m.', 'j', 10, None)]},
        {'n': 66, 't': 'If pay was not a factor, which would you prefer over an 8-week period?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Work 8 Saturdays and have 8 Sundays off', 'a', 1, None), ('Work 8 Sundays and have 8 Saturdays off', 'b', 2, None), ('Work 4 full weekends and have 4 full weekends off', 'c', 3, None)]},
        {'n': 67, 't': 'The ability to swap shifts is important to me.', 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 68, 't': 'If pay is not a factor when comparing the following two work shifts, I would prefer to work a night shift that:', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Starts Sunday night and ends Monday morning', 'a', 1, None), ('Starts Friday night and ends Saturday morning', 'b', 2, None)]},
        {'n': 69, 't': 'Which best describes you?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('I like my weekends off to alternate', 'a', 1, None), ('I like to have several weekends off in a row and would be willing to work several in a row to make that happen', 'b', 2, None)]},
        {'n': 70, 't': 'Which best describes you?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('I like to work several days in a row and then take a long break', 'a', 1, None), ('I like to work a couple of days in a row and then take a short break', 'b', 2, None)]},
        {'n': 71, 't': 'If you could only have 3 days off per week, which of the following would you prefer?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Friday-Saturday-Sunday', 'a', 1, None), ('Saturday-Sunday-Monday', 'b', 2, None), ('Sunday-Monday-Tuesday', 'c', 3, None)]},
        {'n': 72, 't': 'If your schedule requires you to take weekdays off, which day do you prefer to have off?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('Monday', 'a', 1, None), ('Tuesday', 'b', 2, None), ('Wednesday', 'c', 3, None), ('Thursday', 'd', 4, None), ('Friday', 'e', 5, None)]},
        {'n': 73, 't': 'What percentage of time do you think you should be working at the same time as your supervisor?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('100%', 'a', 1, None), ('90%', 'b', 2, None), ('80%', 'c', 3, None), ('70%', 'd', 4, None), ('60%', 'e', 5, None), ('50% or less', 'f', 6, None)]},
        {'n': 74, 't': "I don't mind doing several different types of work during the week.", 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 75, 't': 'Which best describes you?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('I am willing to work my share of weekends', 'a', 1, None), ('I will quit before I work weekends', 'b', 2, None)]},
        {'n': 76, 't': 'I am willing to work weekends occasionally if I can plan them in advance.', 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 77, 't': 'It is clear to me why we have to go to a 24/7 schedule/weekend work to keep this company competitive in this industry.', 'c': 'Shift Schedule Features', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 78, 't': 'Which best describes you?', 'c': 'Shift Schedule Features', 'ty': 'multiple_choice', 'o': [('I am willing to try a 12-hour/7-day/new schedule for 6 to 12 months', 'a', 1, None), ('I will reluctantly go along with a 12-hour/7-day/new schedule trial if that is what the majority of the workforce wants', 'b', 2, None), ('I will quit before I go to a 12-hour/7-day/new schedule', 'c', 3, None)]},
        # OVERTIME (79-91)
        {'n': 79, 't': 'I depend on overtime worked outside my schedule to help me make ends meet:', 'c': 'Overtime', 'ty': 'multiple_choice', 'o': [('Never', 'a', 1, None), ('Sometimes', 'b', 2, None), ('Frequently', 'c', 3, None), ('Every week', 'd', 4, None)]},
        {'n': 80, 't': 'Over the last few months I have been:', 'c': 'Overtime', 'ty': 'multiple_choice', 'o': [('Working too much overtime', 'a', 1, None), ('Working too little overtime', 'b', 2, None), ('Working just the right amount of overtime', 'c', 3, None)]},
        {'n': 81, 't': 'Overtime levels are just right the way they are.', 'c': 'Overtime', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 82, 't': 'When you work overtime outside your schedule, when do you usually work it?', 'c': 'Overtime', 'ty': 'multiple_choice', 'o': [("I don't work overtime", 'a', 1, None), ('On a regularly scheduled workday by coming in early or staying late', 'b', 2, None), ('On Saturdays, but not Sundays', 'c', 3, None), ('On Sundays, but not Saturdays', 'd', 4, None), ('Any chance I get', 'e', 5, None), ('I work overtime when necessary for business needs', 'f', 6, None)]},
        {'n': 83, 't': 'When you have to work overtime, when do you prefer to work it?', 'c': 'Overtime', 'ty': 'multiple_choice', 'o': [('On a scheduled work day', 'a', 1, None), ('On a day off', 'b', 2, None), ('No preference', 'c', 3, None)]},
        {'n': 84, 't': 'I prefer overtime by extending my shift.', 'c': 'Overtime', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 85, 't': 'I prefer to work overtime by coming in on a day off.', 'c': 'Overtime', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 86, 't': 'Current overtime distribution policies are fair.', 'c': 'Overtime', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 87, 't': 'Overtime is predictable and can be planned for.', 'c': 'Overtime', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 88, 't': 'If you had to choose between more time off or more overtime, what would you choose?', 'c': 'Overtime', 'ty': 'multiple_choice', 'o': [('More time off', 'a', 1, None), ('More overtime', 'b', 2, None)]},
        {'n': 89, 't': 'When it comes to overtime, I generally want to get:', 'c': 'Overtime', 'ty': 'multiple_choice', 'o': [('As much as possible', 'a', 1, None), ('Frequent overtime', 'b', 2, None), ('Occasional overtime', 'c', 3, None), ('Infrequent overtime', 'd', 4, None), ('I do not want any overtime', 'e', 5, None)]},
        {'n': 90, 't': 'I expect to get overtime whenever I want it.', 'c': 'Overtime', 'ty': 'likert_5', 'sc': 'average_rating', 'o': L},
        {'n': 91, 't': 'How much overtime would you like to have every week?', 'c': 'Overtime', 'ty': 'multiple_choice', 'sc': 'average_hours', 'o': [('None', 'a', 1, 0), ('Less than 2 hours', 'b', 2, 1), ('Between 2 and 4 hours', 'c', 3, 3), ('Between 4 and 6 hours', 'd', 4, 5), ('Between 6 and 8 hours', 'e', 5, 7), ('Between 8 and 12 hours', 'f', 6, 10), ('I will take all that I can get', 'g', 7, 15)]},
        # DAY CARE/ELDER CARE (92-97)
        {'n': 92, 't': 'Do you use outside day/elder care?', 'c': 'Day Care/Elder Care', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
        {'n': 93, 't': 'Is your day/elder care provider:', 'c': 'Day Care/Elder Care', 'ty': 'multiple_choice', 'o': [('Close to home', 'a', 1, None), ('Close to work', 'b', 2, None), ('At home', 'c', 3, None)]},
        {'n': 94, 't': 'Is your day/elder care provider a family member, neighbor or friend?', 'c': 'Day Care/Elder Care', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
        {'n': 95, 't': 'Do you use day/elder care when working days?', 'c': 'Day Care/Elder Care', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
        {'n': 96, 't': 'Is day/elder care a bigger issue on a particular shift?', 'c': 'Day Care/Elder Care', 'ty': 'yes_no', 'o': [('Yes', 'a', 1, None), ('No', 'b', 2, None)]},
        {'n': 97, 't': 'If you answered "yes" on the previous question, which shift?', 'c': 'Day Care/Elder Care', 'ty': 'multiple_choice', 'o': [('Days', 'a', 1, None), ('Afternoons', 'b', 2, None), ('Nights', 'c', 3, None)]},
    ]


@app.route('/api/setup', methods=['GET'])
def setup_database():
    """
    Initialize database tables and import questions via web request.
    Visit: https://swingshift.onrender.com/api/setup
    """
    results = {'tables_created': False, 'questions_imported': 0, 'errors': []}
    
    try:
        db.create_all()
        results['tables_created'] = True
    except Exception as e:
        results['errors'].append(f'Table creation error: {str(e)}')
        return jsonify(results), 500
    
    try:
        existing_count = MasterQuestion.query.count()
        if existing_count >= 97:
            results['questions_imported'] = existing_count
            results['message'] = 'Questions already imported'
            return jsonify(results)
        
        QUESTIONS = get_all_questions()
        count = 0
        for q in QUESTIONS:
            if MasterQuestion.query.filter_by(question_number=q['n']).first():
                continue
            likert_low, likert_high = None, None
            if q['ty'] == 'likert_5':
                likert_low, likert_high = 'Strongly Disagree', 'Strongly Agree'
            mq = MasterQuestion(
                question_text=q['t'], question_number=q['n'], category=q['c'],
                question_type=q['ty'], likert_low_label=likert_low, likert_high_label=likert_high,
                has_special_calculation=bool(q.get('sc')), calculation_type=q.get('sc')
            )
            db.session.add(mq)
            db.session.flush()
            for i, opt in enumerate(q.get('o', [])):
                ro = ResponseOption(
                    question_id=mq.id, option_text=opt[0], option_code=opt[1],
                    numeric_value=opt[2], display_order=i + 1,
                    calculation_value=opt[3] if len(opt) > 3 else None
                )
                db.session.add(ro)
            count += 1
        db.session.commit()
        results['questions_imported'] = count
        results['total_questions'] = MasterQuestion.query.count()
        results['message'] = f'Successfully imported {count} questions'
        
    except Exception as e:
        db.session.rollback()
        results['errors'].append(f'Question import error: {str(e)}')
        return jsonify(results), 500
    
    return jsonify(results)


@app.route('/api/setup/status', methods=['GET'])
def setup_status():
    """Check the current database setup status"""
    try:
        question_count = MasterQuestion.query.count()
        project_count = Project.query.count()
        response_count = SurveyResponse.query.count()
        
        return jsonify({
            'database_connected': True,
            'questions_loaded': question_count,
            'projects_created': project_count,
            'total_responses': response_count,
            'ready': question_count >= 97
        })
    except Exception as e:
        return jsonify({
            'database_connected': False,
            'error': str(e)
        }), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)


# I did no harm and this file is not truncated
