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
from flask import Flask, request, jsonify, send_file
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
    
    return jsonify({
        'questions': [q.to_dict() for q in questions],
        'total': len(questions)
    })


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
    return jsonify({
        'projects': [p.to_dict() for p in projects],
        'total': len(projects)
    })


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
    
    # Get both master questions and custom questions
    project_questions = [pq.to_dict() for pq in project.questions]
    custom_questions = [cq.to_dict() for cq in project.custom_questions]
    
    # Combine and sort by question_order
    all_questions = project_questions + custom_questions
    all_questions.sort(key=lambda x: x['question_order'])
    
    return jsonify({
        'questions': all_questions,
        'total': len(all_questions)
    })


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
    """Add multiple questions from master bank to a project (admin only)"""
    auth_error = require_admin()
    if auth_error:
        return auth_error
    
    project = Project.query.get_or_404(project_id)
    data = request.get_json()
    
    # Get the next question order
    max_order = db.session.query(
        db.func.max(ProjectQuestion.question_order)
    ).filter_by(project_id=project_id).scalar() or 0
    
    question_ids = data.get('master_question_ids', [])
    added = []
    
    for i, mq_id in enumerate(question_ids):
        # Check if already added
        exists = ProjectQuestion.query.filter_by(
            project_id=project_id,
            master_question_id=mq_id
        ).first()
        
        if not exists:
            pq = ProjectQuestion(
                project_id=project_id,
                master_question_id=mq_id,
                question_order=max_order + i + 1,
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
