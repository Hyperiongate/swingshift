"""
SwingShift Survey System - Database Models
==========================================
Last Updated: January 17, 2026

CHANGES IN THIS VERSION:
- Added MasterVideo model for Master Video Library
- Allows Jim to maintain a permanent library of schedule videos
- Videos can be selected per-project from the master library

This file defines all database tables for the survey system:
- MasterQuestion: The question bank (97+ questions from Shiftwork Solutions)
- ResponseOption: Answer choices for each question
- Project: Client projects/surveys
- ProjectQuestion: Questions selected for a specific project
- CustomQuestion: Client-specific questions added to a project
- ScheduleVideo: Schedule videos uploaded for a project (up to 6)
- MasterVideo: Master library of reusable schedule videos (NEW)
- SurveyResponse: Individual employee responses
- ResponseAnswer: Individual answers within a response
- ScheduleRating: Employee ratings of schedule videos
- NormativeData: Benchmark data from hundreds of past surveys

NOTES FOR FUTURE AI:
- Questions are organized by category (Demographics, Health, Working Conditions, etc.)
- Response options can be Likert scales (1-5), Yes/No, or multiple choice
- Each project gets a unique access_code for anonymous survey access
- Clients access their project via /project/{access_code}
- NormativeData stores benchmark percentages for comparison
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()


class MasterQuestion(db.Model):
    """
    The question bank - contains all standard survey questions.
    These are the 97+ questions developed over 30+ years of consulting.
    """
    __tablename__ = 'master_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Question content
    question_text = db.Column(db.Text, nullable=False)
    question_number = db.Column(db.Integer, nullable=False)  # Original question number from master survey
    
    # Categorization
    category = db.Column(db.String(100), nullable=False)  # Demographics, Health, Working Conditions, etc.
    subcategory = db.Column(db.String(100), nullable=True)  # More specific grouping
    
    # Question type
    question_type = db.Column(db.String(50), nullable=False)  
    # Types: 'multiple_choice', 'likert_5', 'yes_no', 'open_text', 'multi_select'
    
    # For Likert scales
    likert_low_label = db.Column(db.String(100), nullable=True)  # e.g., "Strongly Disagree"
    likert_high_label = db.Column(db.String(100), nullable=True)  # e.g., "Strongly Agree"
    
    # For special calculations (averages, etc.)
    has_special_calculation = db.Column(db.Boolean, default=False)
    calculation_type = db.Column(db.String(50), nullable=True)  # 'average_rating', 'average_hours', 'average_miles', etc.
    
    # Metadata
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    response_options = db.relationship('ResponseOption', backref='question', lazy='dynamic', 
                                       order_by='ResponseOption.display_order')
    normative_data = db.relationship('NormativeData', backref='question', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'question_text': self.question_text,
            'question_number': self.question_number,
            'category': self.category,
            'subcategory': self.subcategory,
            'question_type': self.question_type,
            'likert_low_label': self.likert_low_label,
            'likert_high_label': self.likert_high_label,
            'has_special_calculation': self.has_special_calculation,
            'calculation_type': self.calculation_type,
            'response_options': [opt.to_dict() for opt in self.response_options],
        }


class ResponseOption(db.Model):
    """
    Answer choices for each question.
    Stores both display text and the code used for data analysis.
    """
    __tablename__ = 'response_options'
    
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('master_questions.id'), nullable=False)
    
    option_text = db.Column(db.String(500), nullable=False)  # What the user sees
    option_code = db.Column(db.String(10), nullable=True)  # For encoding (a, b, c or 1, 2, 3)
    numeric_value = db.Column(db.Float, nullable=True)  # For calculations (Likert: 1-5, miles: midpoint)
    display_order = db.Column(db.Integer, nullable=False)  # Order shown to user
    
    # For special calculations
    calculation_value = db.Column(db.Float, nullable=True)  # e.g., midpoint of "1 to 5 miles" = 3
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'option_text': self.option_text,
            'option_code': self.option_code,
            'numeric_value': self.numeric_value,
            'display_order': self.display_order,
            'calculation_value': self.calculation_value,
        }


class Project(db.Model):
    """
    A client project/survey engagement.
    Each project has a unique access code for anonymous survey access.
    Clients access setup/results via /project/{access_code}
    """
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Project identification
    project_name = db.Column(db.String(200), nullable=False)  # Usually company name
    company_name = db.Column(db.String(200), nullable=False)
    
    # Survey access
    access_code = db.Column(db.String(50), unique=True, nullable=False)  # Unique URL identifier
    client_password = db.Column(db.String(200), nullable=True)  # Optional password for client portal
    
    # Status
    status = db.Column(db.String(50), default='draft')  # draft, active, closed, completed
    
    # Survey settings
    is_anonymous = db.Column(db.Boolean, default=True)
    show_progress = db.Column(db.Boolean, default=True)
    randomize_options = db.Column(db.Boolean, default=False)
    
    # Employee identifier label (what client calls it)
    employee_id_label = db.Column(db.String(100), default='Employee Number')
    require_employee_id = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    opened_at = db.Column(db.DateTime, nullable=True)  # When survey went active
    closed_at = db.Column(db.DateTime, nullable=True)  # When survey was closed
    
    # Relationships
    questions = db.relationship('ProjectQuestion', backref='project', lazy='dynamic',
                               order_by='ProjectQuestion.question_order')
    custom_questions = db.relationship('CustomQuestion', backref='project', lazy='dynamic',
                                       order_by='CustomQuestion.question_order')
    responses = db.relationship('SurveyResponse', backref='project', lazy='dynamic')
    schedules = db.relationship('ScheduleVideo', backref='project', lazy='dynamic',
                               order_by='ScheduleVideo.display_order')
    
    def __init__(self, **kwargs):
        super(Project, self).__init__(**kwargs)
        if not self.access_code:
            self.access_code = str(uuid.uuid4())[:8].upper()
    
    def to_dict(self):
        return {
            'id': self.id,
            'project_name': self.project_name,
            'company_name': self.company_name,
            'access_code': self.access_code,
            'status': self.status,
            'is_anonymous': self.is_anonymous,
            'show_progress': self.show_progress,
            'employee_id_label': self.employee_id_label,
            'require_employee_id': self.require_employee_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'response_count': self.responses.count(),
            'question_count': self.questions.count() + self.custom_questions.count(),
            'schedule_count': self.schedules.count(),
        }


class ProjectQuestion(db.Model):
    """
    Questions selected from the master bank for a specific project.
    Links master questions to projects with custom ordering.
    """
    __tablename__ = 'project_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    master_question_id = db.Column(db.Integer, db.ForeignKey('master_questions.id'), nullable=False)
    
    question_order = db.Column(db.Integer, nullable=False)  # Order in this survey (Q1, Q2, Q3...)
    
    # Option to customize question text for this project
    custom_text = db.Column(db.Text, nullable=True)  # If null, use master question text
    
    # Custom response options for this project (JSON array of {text, code})
    custom_options_json = db.Column(db.Text, nullable=True)  # If set, overrides master question options
    
    # For breakout analysis
    is_breakout = db.Column(db.Boolean, default=False)  # Use this question for segmentation
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to master question
    master_question = db.relationship('MasterQuestion')
    
    def to_dict(self):
        import json
        mq = self.master_question
        
        # Use custom options if set, otherwise use master question options
        if self.custom_options_json:
            try:
                custom_opts = json.loads(self.custom_options_json)
                response_options = [
                    {'option_text': opt['text'], 'option_code': opt['code'], 'numeric_value': i + 1, 'display_order': i + 1}
                    for i, opt in enumerate(custom_opts)
                ]
            except:
                response_options = [opt.to_dict() for opt in mq.response_options]
        else:
            response_options = [opt.to_dict() for opt in mq.response_options]
        
        return {
            'id': self.id,
            'project_id': self.project_id,
            'question_order': self.question_order,
            'is_breakout': self.is_breakout,
            'question_text': self.custom_text or mq.question_text,
            'question_type': mq.question_type,
            'category': mq.category,
            'likert_low_label': mq.likert_low_label,
            'likert_high_label': mq.likert_high_label,
            'response_options': response_options,
            'master_question_id': mq.id,
            'question_number': mq.question_number,
            'has_custom_options': bool(self.custom_options_json),
        }


class CustomQuestion(db.Model):
    """
    Custom questions added specifically for a project.
    Not from the master bank - created for specific client needs.
    """
    __tablename__ = 'custom_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    
    question_text = db.Column(db.Text, nullable=False)
    question_order = db.Column(db.Integer, nullable=False)
    question_type = db.Column(db.String(50), nullable=False)  # Same types as MasterQuestion
    
    # For Likert scales
    likert_low_label = db.Column(db.String(100), nullable=True)
    likert_high_label = db.Column(db.String(100), nullable=True)
    
    # For breakout analysis
    is_breakout = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    response_options = db.relationship('CustomResponseOption', backref='question', lazy='dynamic',
                                       order_by='CustomResponseOption.display_order')
    
    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'question_order': self.question_order,
            'question_text': self.question_text,
            'question_type': self.question_type,
            'likert_low_label': self.likert_low_label,
            'likert_high_label': self.likert_high_label,
            'is_breakout': self.is_breakout,
            'is_custom': True,
            'response_options': [opt.to_dict() for opt in self.response_options],
        }


class CustomResponseOption(db.Model):
    """
    Response options for custom questions.
    """
    __tablename__ = 'custom_response_options'
    
    id = db.Column(db.Integer, primary_key=True)
    custom_question_id = db.Column(db.Integer, db.ForeignKey('custom_questions.id'), nullable=False)
    
    option_text = db.Column(db.String(500), nullable=False)
    option_code = db.Column(db.String(10), nullable=True)
    numeric_value = db.Column(db.Float, nullable=True)
    display_order = db.Column(db.Integer, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'option_text': self.option_text,
            'option_code': self.option_code,
            'numeric_value': self.numeric_value,
            'display_order': self.display_order,
        }


class SurveyResponse(db.Model):
    """
    A single employee's survey response session.
    Contains metadata about the response (timestamp, completion status).
    Individual answers are in ResponseAnswer.
    """
    __tablename__ = 'survey_responses'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    
    # Response metadata
    response_code = db.Column(db.String(50), unique=True, nullable=False)  # Unique identifier
    
    # Status
    is_complete = db.Column(db.Boolean, default=False)
    
    # Timestamps
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Optional metadata (for tracking, not identification)
    user_agent = db.Column(db.String(500), nullable=True)
    ip_hash = db.Column(db.String(64), nullable=True)  # Hashed for privacy
    
    # Relationships
    answers = db.relationship('ResponseAnswer', backref='response', lazy='dynamic')
    
    def __init__(self, **kwargs):
        super(SurveyResponse, self).__init__(**kwargs)
        if not self.response_code:
            self.response_code = str(uuid.uuid4())
    
    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'response_code': self.response_code,
            'is_complete': self.is_complete,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'answer_count': self.answers.count(),
        }


class ResponseAnswer(db.Model):
    """
    Individual answer to a single question within a response.
    """
    __tablename__ = 'response_answers'
    
    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey('survey_responses.id'), nullable=False)
    
    # Which question (can be project question or custom question)
    project_question_id = db.Column(db.Integer, db.ForeignKey('project_questions.id'), nullable=True)
    custom_question_id = db.Column(db.Integer, db.ForeignKey('custom_questions.id'), nullable=True)
    
    # The actual answer
    answer_text = db.Column(db.Text, nullable=True)  # The selected option text or open-ended response
    answer_code = db.Column(db.String(10), nullable=True)  # Encoded value (a, b, c or 1, 2, 3)
    answer_numeric = db.Column(db.Float, nullable=True)  # Numeric value for calculations
    
    # For multi-select questions
    answer_multi = db.Column(db.JSON, nullable=True)  # List of selected options
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    project_question = db.relationship('ProjectQuestion')
    custom_question = db.relationship('CustomQuestion')
    
    def to_dict(self):
        return {
            'id': self.id,
            'response_id': self.response_id,
            'project_question_id': self.project_question_id,
            'custom_question_id': self.custom_question_id,
            'answer_text': self.answer_text,
            'answer_code': self.answer_code,
            'answer_numeric': self.answer_numeric,
            'answer_multi': self.answer_multi,
        }


class ScheduleVideo(db.Model):
    """
    Schedule videos uploaded for a project.
    Each project can have up to 6 schedule videos for employees to view and rate.
    """
    __tablename__ = 'schedule_videos'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    
    # Video identification
    schedule_name = db.Column(db.String(200), nullable=False)  # e.g., "4-crew 12-hour"
    schedule_description = db.Column(db.Text, nullable=True)  # Brief description
    display_order = db.Column(db.Integer, nullable=False)  # 1-6
    
    # Video file
    video_filename = db.Column(db.String(500), nullable=False)  # Stored filename
    original_filename = db.Column(db.String(500), nullable=True)  # Original upload name
    video_url = db.Column(db.String(1000), nullable=True)  # If using external hosting
    
    # Metadata
    duration_seconds = db.Column(db.Integer, nullable=True)
    file_size_bytes = db.Column(db.Integer, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ratings = db.relationship('ScheduleRating', backref='schedule', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'schedule_name': self.schedule_name,
            'schedule_description': self.schedule_description,
            'display_order': self.display_order,
            'video_filename': self.video_filename,
            'original_filename': self.original_filename,
            'video_url': self.video_url,
            'duration_seconds': self.duration_seconds,
            'rating_count': self.ratings.count(),
        }


class MasterVideo(db.Model):
    """
    Master Video Library - Jim's curated collection of schedule videos.
    These are reusable across multiple projects.
    When Jim creates a project, he selects 6-10 videos from this library.
    
    Added: January 17, 2026
    """
    __tablename__ = 'master_videos'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Video details
    video_name = db.Column(db.String(200), nullable=False)  # e.g., "Dupont 12-Hour 2-2-3"
    video_description = db.Column(db.Text, nullable=False)  # Brief description Jim writes
    youtube_url = db.Column(db.String(500), nullable=False)  # Full YouTube URL
    video_id = db.Column(db.String(50), nullable=False)  # Extracted video ID for embedding
    
    # Organization
    tags = db.Column(db.String(500), nullable=True)  # Comma-separated: "Manufacturing,12-hour,Rotating"
    duration_minutes = db.Column(db.Integer, nullable=True)  # Optional: video length
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'video_name': self.video_name,
            'video_description': self.video_description,
            'youtube_url': self.youtube_url,
            'video_id': self.video_id,
            'tags': self.tags,
            'duration_minutes': self.duration_minutes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }


class ScheduleRating(db.Model):
    """
    Employee ratings of schedule videos.
    Each employee rates each schedule they view.
    """
    __tablename__ = 'schedule_ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey('survey_responses.id'), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule_videos.id'), nullable=False)
    
    # Rating (1-5 or rank order)
    rating = db.Column(db.Integer, nullable=True)  # 1-5 preference rating
    rank = db.Column(db.Integer, nullable=True)  # 1-6 rank order (1=most preferred)
    
    # Optional comments
    comments = db.Column(db.Text, nullable=True)
    
    # Tracking
    video_watched = db.Column(db.Boolean, default=False)  # Did they watch the full video?
    watch_duration_seconds = db.Column(db.Integer, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'response_id': self.response_id,
            'schedule_id': self.schedule_id,
            'rating': self.rating,
            'rank': self.rank,
            'comments': self.comments,
            'video_watched': self.video_watched,
        }


class NormativeData(db.Model):
    """
    Benchmark data from the normative database (200+ past surveys).
    Stores response percentages for comparison.
    """
    __tablename__ = 'normative_data'
    
    id = db.Column(db.Integer, primary_key=True)
    master_question_id = db.Column(db.Integer, db.ForeignKey('master_questions.id'), nullable=False)
    
    # The response option this data is for
    response_text = db.Column(db.String(500), nullable=False)
    
    # Benchmark statistics
    average_percentage = db.Column(db.Float, nullable=False)  # Average across all surveys
    min_percentage = db.Column(db.Float, nullable=True)
    max_percentage = db.Column(db.Float, nullable=True)
    std_deviation = db.Column(db.Float, nullable=True)
    sample_size = db.Column(db.Integer, nullable=True)  # Number of surveys this is based on
    
    # Optional filtering
    industry = db.Column(db.String(100), nullable=True)  # For industry-specific norms
    company_size = db.Column(db.String(50), nullable=True)  # small, medium, large
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'master_question_id': self.master_question_id,
            'response_text': self.response_text,
            'average_percentage': self.average_percentage,
            'sample_size': self.sample_size,
        }


# I did no harm and this file is not truncated
