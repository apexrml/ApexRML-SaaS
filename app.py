"""
ApexRML SaaS Application
Flask Backend for Dual-Model Hybrid Platform
(Parts Finder + Garage Finder + Recovery Network + AI Diagnostics)

Author: ApexRML Team
Version: 1.0.0
License: Proprietary
"""

import os
import json
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Tuple, Optional
import secrets
import hashlib

# Core Flask & Extensions
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Database
from sqlalchemy import text, func, and_, or_
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid as uuid_lib

# Security & Auth
from werkzeug.security import generate_password_hash, check_password_hash
import jwt as pyjwt

# Email & Communication
from flask_mail import Mail, Message
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail as SGMail

# Payment Processing
import stripe

# Utilities
import requests
from dotenv import load_dotenv
from decimal import Decimal

# Load environment variables
load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_hex(32))
    DEBUG = os.getenv('FLASK_ENV') == 'development'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://user:password@localhost/apexrml_production'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = DEBUG
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', secrets.token_hex(32))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Stripe Configuration
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
    STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
    
    # Email Configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.sendgrid.net')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', True)
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'apikey')
    MAIL_PASSWORD = os.getenv('SENDGRID_API_KEY', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@apexrml.co.uk')
    
    # External APIs
    DVLA_API_KEY = os.getenv('DVLA_API_KEY', '')
    EBAY_EPN_TOKEN = os.getenv('EBAY_EPN_TOKEN', '')
    AWIN_API_KEY = os.getenv('AWIN_API_KEY', '')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    
    # Frontend
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    
    # Security
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# ============================================================================
# APPLICATION FACTORY
# ============================================================================

def create_app(config_class=Config):
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors = CORS(app, origins=app.config['CORS_ORIGINS'])
    limiter.init_app(app)
    mail.init_app(app)
    
    # Configure Stripe
    stripe.api_key = app.config['STRIPE_SECRET_KEY']
    
    # Setup logging
    setup_logging(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register CLI commands
    register_cli_commands(app)
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    return app

# ============================================================================
# EXTENSIONS
# ============================================================================

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)
mail = Mail()

# ============================================================================
# MODELS
# ============================================================================

class User(db.Model):
    """User model - Core authentication"""
    __tablename__ = 'users'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(500), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    phone_number = db.Column(db.String(20))
    user_type = db.Column(db.String(50), nullable=False, default='customer')  # customer, garage, recovery_driver, admin
    
    # Authentication
    email_verified = db.Column(db.Boolean, default=False)
    email_verified_at = db.Column(db.DateTime)
    verification_token = db.Column(db.String(500))
    
    # OAuth
    oauth_provider = db.Column(db.String(50))
    oauth_id = db.Column(db.String(500))
    oauth_token = db.Column(db.String(1000))
    
    # Status
    status = db.Column(db.String(50), default='pending')  # pending, active, suspended, deleted
    last_login_at = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, default=0)
    
    # Metadata
    avatar_url = db.Column(db.Text)
    preferences = db.Column(JSONB, default={})
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)
    
    # Relationships
    organizations = db.relationship('Organization', backref='owner', foreign_keys='Organization.owner_id')
    member_organizations = db.relationship('OrganizationMember', backref='user')
    leads = db.relationship('GarageLead', backref='customer')
    recovery_drivers = db.relationship('RecoveryDriver', backref='user')
    
    def set_password(self, password: str):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def generate_verification_token(self) -> str:
        """Generate email verification token"""
        self.verification_token = secrets.token_urlsafe(32)
        return self.verification_token
    
    def verify_email(self) -> bool:
        """Mark email as verified"""
        self.email_verified = True
        self.email_verified_at = datetime.utcnow()
        self.verification_token = None
        self.status = 'active'
        db.session.commit()
        return True
    
    def to_dict(self) -> dict:
        """Serialize user"""
        return {
            'id': str(self.id),
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone_number': self.phone_number,
            'user_type': self.user_type,
            'email_verified': self.email_verified,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
        }

class Organization(db.Model):
    """Organization model - Multi-tenant support"""
    __tablename__ = 'organizations'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    owner_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    
    # Basic Info
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text)
    website = db.Column(db.String(255))
    phone_number = db.Column(db.String(20))
    email = db.Column(db.String(255))
    
    # Organization Type
    org_type = db.Column(db.String(50), nullable=False)  # garage, recovery_network, etc
    
    # Address
    address_line_1 = db.Column(db.String(255))
    address_line_2 = db.Column(db.String(255))
    city = db.Column(db.String(100))
    postcode = db.Column(db.String(20))
    country_code = db.Column(db.String(2), default='GB')
    
    # Business Details
    company_registration = db.Column(db.String(50))
    vat_number = db.Column(db.String(50))
    employees_count = db.Column(db.Integer)
    
    # Branding
    logo_url = db.Column(db.Text)
    banner_url = db.Column(db.Text)
    brand_color = db.Column(db.String(10))
    
    # Subscription
    subscription_plan = db.Column(db.String(50), default='free')
    subscription_status = db.Column(db.String(50), default='active')
    subscription_started_at = db.Column(db.DateTime)
    subscription_ends_at = db.Column(db.DateTime)
    stripe_customer_id = db.Column(db.String(255))
    stripe_subscription_id = db.Column(db.String(255))
    
    # Status
    status = db.Column(db.String(50), default='active')
    
    # Metadata
    metadata = db.Column(JSONB, default={})
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    members = db.relationship('OrganizationMember', backref='organization', cascade='all, delete-orphan')
    garages = db.relationship('Garage', backref='organization', cascade='all, delete-orphan')
    subscriptions = db.relationship('Subscription', backref='organization', cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', backref='organization', cascade='all, delete-orphan')
    
    def to_dict(self) -> dict:
        """Serialize organization"""
        return {
            'id': str(self.id),
            'name': self.name,
            'slug': self.slug,
            'org_type': self.org_type,
            'subscription_plan': self.subscription_plan,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
        }

class OrganizationMember(db.Model):
    """Organization member model"""
    __tablename__ = 'organization_members'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    organization_id = db.Column(UUID(as_uuid=True), db.ForeignKey('organizations.id'), nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    
    role = db.Column(db.String(50), default='member')  # owner, admin, manager, member, viewer
    permissions = db.Column(JSONB, default=['read'])
    status = db.Column(db.String(50), default='active')
    invited_at = db.Column(db.DateTime)
    joined_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('organization_id', 'user_id', name='unique_org_user'),)

class Garage(db.Model):
    """Garage model - Garage Finder B2B SaaS"""
    __tablename__ = 'garages'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    organization_id = db.Column(UUID(as_uuid=True), db.ForeignKey('organizations.id'), nullable=False, index=True)
    
    garage_name = db.Column(db.String(255), nullable=False)
    garage_type = db.Column(db.String(100))
    phone_number = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    
    # Address
    address_line_1 = db.Column(db.String(255))
    address_line_2 = db.Column(db.String(255))
    city = db.Column(db.String(100))
    postcode = db.Column(db.String(20), index=True)
    latitude = db.Column(db.Numeric(10, 8))
    longitude = db.Column(db.Numeric(11, 8))
    
    # Services
    services = db.Column(JSONB, default=['diagnostics', 'repairs', 'maintenance'])
    vehicle_brands = db.Column(db.ARRAY(db.String(50)))
    equipment_list = db.Column(JSONB)
    
    # Capacity
    bays_available = db.Column(db.Integer)
    technicians_count = db.Column(db.Integer)
    
    # Ratings
    average_rating = db.Column(db.Numeric(3, 2), default=0)
    total_reviews = db.Column(db.Integer, default=0)
    response_time_hours = db.Column(db.Integer, default=24)
    
    # Features
    online_booking_enabled = db.Column(db.Boolean, default=False)
    accepts_walkins = db.Column(db.Boolean, default=True)
    mobile_service_available = db.Column(db.Boolean, default=False)
    
    # Lead Management
    leads_received = db.Column(db.Integer, default=0)
    leads_converted = db.Column(db.Integer, default=0)
    
    # Verification
    verified = db.Column(db.Boolean, default=False)
    verification_date = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    leads = db.relationship('GarageLead', backref='garage', cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='garage', cascade='all, delete-orphan')
    
    def to_dict(self) -> dict:
        """Serialize garage"""
        return {
            'id': str(self.id),
            'garage_name': self.garage_name,
            'garage_type': self.garage_type,
            'city': self.city,
            'postcode': self.postcode,
            'average_rating': float(self.average_rating) if self.average_rating else 0,
            'total_reviews': self.total_reviews,
            'services': self.services,
            'verified': self.verified,
        }

class GarageLead(db.Model):
    """Lead model - Garage Finder lead management"""
    __tablename__ = 'garage_leads'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    garage_id = db.Column(UUID(as_uuid=True), db.ForeignKey('garages.id'), nullable=False, index=True)
    customer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)
    
    # Vehicle
    vehicle_registration = db.Column(db.String(10))
    vehicle_make = db.Column(db.String(50))
    vehicle_model = db.Column(db.String(50))
    vehicle_year = db.Column(db.Integer)
    
    # Issue
    issue_description = db.Column(db.Text, nullable=False)
    issue_category = db.Column(db.String(100))
    priority = db.Column(db.String(20), default='medium')
    
    # Status
    status = db.Column(db.String(50), default='new', index=True)
    status_updated_at = db.Column(db.DateTime)
    
    # Pricing
    estimated_cost_low = db.Column(db.Numeric(8, 2))
    estimated_cost_high = db.Column(db.Numeric(8, 2))
    final_cost = db.Column(db.Numeric(8, 2))
    
    # Timeline
    preferred_date_from = db.Column(db.Date)
    preferred_date_to = db.Column(db.Date)
    estimated_duration_hours = db.Column(db.Integer)
    actual_duration_hours = db.Column(db.Integer)
    
    # Customer Feedback
    customer_rating = db.Column(db.Integer)
    customer_feedback = db.Column(db.Text)
    garage_notes = db.Column(db.Text)
    
    # Contact
    customer_phone = db.Column(db.String(20))
    customer_email = db.Column(db.String(255))
    preferred_contact_method = db.Column(db.String(20))
    
    # Source
    lead_source = db.Column(db.String(50), default='apexrml')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reviews = db.relationship('Review', backref='lead')
    
    def to_dict(self) -> dict:
        """Serialize lead"""
        return {
            'id': str(self.id),
            'vehicle_registration': self.vehicle_registration,
            'issue_description': self.issue_description,
            'status': self.status,
            'priority': self.priority,
            'estimated_cost_low': float(self.estimated_cost_low) if self.estimated_cost_low else None,
            'estimated_cost_high': float(self.estimated_cost_high) if self.estimated_cost_high else None,
            'created_at': self.created_at.isoformat(),
        }

class Subscription(db.Model):
    """Subscription model - SaaS billing"""
    __tablename__ = 'subscriptions'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    organization_id = db.Column(UUID(as_uuid=True), db.ForeignKey('organizations.id'), nullable=False, index=True)
    
    plan_name = db.Column(db.String(50), nullable=False)  # free, starter, pro, enterprise
    product_type = db.Column(db.String(50), nullable=False)  # garage_finder, recovery_network, ai_diagnostics
    
    monthly_price = db.Column(db.Numeric(8, 2))
    annual_price = db.Column(db.Numeric(8, 2))
    billing_cycle = db.Column(db.String(20), default='monthly')
    
    # Stripe
    stripe_subscription_id = db.Column(db.String(255))
    stripe_price_id = db.Column(db.String(255))
    
    # Status
    status = db.Column(db.String(50), default='active', index=True)
    trial_ends_at = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    ends_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    
    # Auto-Renewal
    auto_renew = db.Column(db.Boolean, default=True)
    next_billing_date = db.Column(db.Date, index=True)
    
    # Features
    features = db.Column(JSONB, default={})
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    invoices = db.relationship('Invoice', backref='subscription')

class Invoice(db.Model):
    """Invoice model - Payment tracking"""
    __tablename__ = 'invoices'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    organization_id = db.Column(UUID(as_uuid=True), db.ForeignKey('organizations.id'), nullable=False, index=True)
    subscription_id = db.Column(UUID(as_uuid=True), db.ForeignKey('subscriptions.id'), nullable=True)
    
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    stripe_invoice_id = db.Column(db.String(255))
    
    # Amounts (in pence)
    subtotal_pence = db.Column(db.Integer)
    tax_pence = db.Column(db.Integer)
    total_pence = db.Column(db.Integer)
    paid_pence = db.Column(db.Integer, default=0)
    
    # Status
    status = db.Column(db.String(50), default='draft', index=True)
    issued_at = db.Column(db.DateTime)
    due_date = db.Column(db.Date, index=True)
    paid_at = db.Column(db.DateTime)
    
    # Items
    line_items = db.Column(JSONB, default=[])
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Serialize invoice"""
        return {
            'id': str(self.id),
            'invoice_number': self.invoice_number,
            'total_amount_gbp': self.total_pence / 100.0 if self.total_pence else 0,
            'status': self.status,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
        }

class Review(db.Model):
    """Review model - Garage ratings"""
    __tablename__ = 'reviews'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    garage_id = db.Column(UUID(as_uuid=True), db.ForeignKey('garages.id'), nullable=False, index=True)
    reviewer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    lead_id = db.Column(UUID(as_uuid=True), db.ForeignKey('garage_leads.id'), nullable=True)
    
    rating = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255))
    comment = db.Column(db.Text)
    
    # Categories
    quality_of_work = db.Column(db.Integer)
    communication = db.Column(db.Integer)
    price_value = db.Column(db.Integer)
    responsiveness = db.Column(db.Integer)
    
    # Moderation
    verified_purchase = db.Column(db.Boolean, default=True)
    helpful_votes = db.Column(db.Integer, default=0)
    unhelpful_votes = db.Column(db.Integer, default=0)
    reported = db.Column(db.Boolean, default=False)
    approved = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class RecoveryDriver(db.Model):
    """Recovery driver model - Recovery Network B2B SaaS"""
    __tablename__ = 'recovery_drivers'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    organization_id = db.Column(UUID(as_uuid=True), db.ForeignKey('organizations.id'), nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    
    driver_name = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(255))
    
    # Driving license
    driving_license_number = db.Column(db.String(50))
    driving_license_type = db.Column(db.String(20))
    medical_expiry_date = db.Column(db.Date)
    
    # Vehicle
    vehicle_registration = db.Column(db.String(10))
    vehicle_make = db.Column(db.String(50))
    vehicle_model = db.Column(db.String(50))
    vehicle_capacity_tonnes = db.Column(db.Numeric(5, 2))
    equipment_type = db.Column(JSONB, default=['wheel_lift', 'flatbed'])
    
    # Geographic
    primary_postcode_area = db.Column(db.String(10), index=True)
    service_radius_miles = db.Column(db.Integer, default=30)
    latitude = db.Column(db.Numeric(10, 8))
    longitude = db.Column(db.Numeric(11, 8))
    
    # Availability
    status = db.Column(db.String(50), default='inactive', index=True)
    currently_available = db.Column(db.Boolean, default=False)
    on_duty_from = db.Column(db.DateTime)
    on_duty_until = db.Column(db.DateTime)
    
    # Performance
    jobs_completed = db.Column(db.Integer, default=0)
    average_response_time_minutes = db.Column(db.Integer)
    customer_rating = db.Column(db.Numeric(3, 2))
    total_revenue = db.Column(db.Numeric(10, 2), default=0)
    
    # Insurance
    insurance_provider = db.Column(db.String(100))
    policy_number = db.Column(db.String(100))
    insurance_expires_at = db.Column(db.Date)
    
    # Verification
    background_check_completed = db.Column(db.Boolean, default=False)
    background_check_date = db.Column(db.Date)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    recovery_jobs = db.relationship('RecoveryJob', backref='driver')

class RecoveryJob(db.Model):
    """Recovery job model - Job dispatch"""
    __tablename__ = 'recovery_jobs'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    organization_id = db.Column(UUID(as_uuid=True), db.ForeignKey('organizations.id'), nullable=False)
    driver_id = db.Column(UUID(as_uuid=True), db.ForeignKey('recovery_drivers.id'), nullable=True)
    
    job_reference = db.Column(db.String(50), unique=True, nullable=False)
    customer_name = db.Column(db.String(255))
    customer_phone = db.Column(db.String(20))
    customer_email = db.Column(db.String(255))
    
    # Vehicle
    vehicle_registration = db.Column(db.String(10))
    vehicle_make = db.Column(db.String(50))
    vehicle_model = db.Column(db.String(50))
    vehicle_color = db.Column(db.String(50))
    
    # Incident
    incident_description = db.Column(db.Text)
    incident_type = db.Column(db.String(50))
    incident_location_address = db.Column(db.Text)
    incident_latitude = db.Column(db.Numeric(10, 8))
    incident_longitude = db.Column(db.Numeric(11, 8))
    
    # Destination
    destination_address = db.Column(db.Text)
    destination_latitude = db.Column(db.Numeric(10, 8))
    destination_longitude = db.Column(db.Numeric(11, 8))
    
    # Timeline
    incident_date_time = db.Column(db.DateTime)
    job_created_at = db.Column(db.DateTime, default=datetime.utcnow)
    job_assigned_at = db.Column(db.DateTime)
    job_started_at = db.Column(db.DateTime)
    job_completed_at = db.Column(db.DateTime)
    estimated_completion_time = db.Column(db.DateTime)
    
    # Status
    job_status = db.Column(db.String(50), default='pending', index=True)
    
    # Pricing
    mileage_km = db.Column(db.Numeric(8, 2))
    distance_charge = db.Column(db.Numeric(8, 2))
    call_out_charge = db.Column(db.Numeric(8, 2))
    additional_charges = db.Column(db.Numeric(8, 2))
    total_cost = db.Column(db.Numeric(10, 2))
    
    # Insurance
    claim_reference = db.Column(db.String(50))
    insurance_company = db.Column(db.String(100))
    insured_recovery = db.Column(db.Boolean, default=False)
    
    # Notes
    driver_notes = db.Column(db.Text)
    support_notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Diagnostic(db.Model):
    """AI diagnostic model"""
    __tablename__ = 'diagnostics'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)
    garage_id = db.Column(UUID(as_uuid=True), db.ForeignKey('garages.id'), nullable=True)
    
    # Vehicle
    vehicle_registration = db.Column(db.String(10))
    vehicle_make = db.Column(db.String(50))
    vehicle_model = db.Column(db.String(50))
    vehicle_year = db.Column(db.Integer)
    vehicle_mileage = db.Column(db.Integer)
    
    # Symptom
    symptom_description = db.Column(db.Text, nullable=False)
    symptom_category = db.Column(db.String(100))
    issue_severity = db.Column(db.String(20))
    issue_duration = db.Column(db.String(100))
    
    # AI Analysis
    ai_diagnosis = db.Column(db.Text)
    possible_fault_codes = db.Column(JSONB)
    recommended_parts = db.Column(JSONB)
    estimated_repair_cost_low = db.Column(db.Numeric(8, 2))
    estimated_repair_cost_high = db.Column(db.Numeric(8, 2))
    
    # Confidence
    confidence_score = db.Column(db.Numeric(5, 2))
    requires_professional_inspection = db.Column(db.Boolean, default=False)
    
    # Action
    quote_generated = db.Column(db.Boolean, default=False)
    is_premium = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(db.Model):
    """Audit log model"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)
    organization_id = db.Column(UUID(as_uuid=True), db.ForeignKey('organizations.id'), nullable=True)
    
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(UUID(as_uuid=True))
    
    changes = db.Column(JSONB, default={})
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    status_code = db.Column(db.Integer)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

# ============================================================================
# BLUEPRINTS & ROUTES
# ============================================================================

def register_blueprints(app):
    """Register all route blueprints"""
    from flask import Blueprint
    
    # Authentication routes
    auth_bp = create_auth_blueprint()
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    
    # Garage Finder routes
    garage_bp = create_garage_blueprint()
    app.register_blueprint(garage_bp, url_prefix='/api/garages')
    
    # Lead management routes
    leads_bp = create_leads_blueprint()
    app.register_blueprint(leads_bp, url_prefix='/api/leads')
    
    # Billing/Subscription routes
    billing_bp = create_billing_blueprint()
    app.register_blueprint(billing_bp, url_prefix='/api/billing')
    
    # Recovery Network routes
    recovery_bp = create_recovery_blueprint()
    app.register_blueprint(recovery_bp, url_prefix='/api/recovery')
    
    # Admin dashboard routes
    admin_bp = create_admin_blueprint()
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    
    # Health check
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        }), 200

def create_auth_blueprint():
    """Authentication routes"""
    bp = Blueprint('auth', __name__)
    
    @bp.route('/register', methods=['POST'])
    @limiter.limit("5 per minute")
    def register():
        """User registration"""
        data = request.get_json()
        
        # Validation
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Missing required fields'}), 400
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 409
        
        # Create user
        user = User(
            email=data['email'],
            user_type=data.get('user_type', 'customer'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
        )
        user.set_password(data['password'])
        user.generate_verification_token()
        
        db.session.add(user)
        db.session.commit()
        
        # Send verification email
        send_verification_email(user)
        
        return jsonify({
            'message': 'Registration successful. Check your email to verify.',
            'user': user.to_dict()
        }), 201
    
    @bp.route('/login', methods=['POST'])
    @limiter.limit("10 per minute")
    def login():
        """User login"""
        data = request.get_json()
        
        user = User.query.filter_by(email=data.get('email')).first()
        if not user or not user.check_password(data.get('password')):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if user.status == 'suspended':
            return jsonify({'error': 'Account suspended'}), 403
        
        if not user.email_verified:
            return jsonify({'error': 'Email not verified'}), 403
        
        # Update login info
        user.last_login_at = datetime.utcnow()
        user.login_count += 1
        db.session.commit()
        
        # Create tokens
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_access_token(identity=str(user.id), expires_delta=timedelta(days=30))
        
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict()
        }), 200
    
    @bp.route('/verify/<token>', methods=['POST'])
    def verify_email(token):
        """Verify email address"""
        user = User.query.filter_by(verification_token=token).first()
        if not user:
            return jsonify({'error': 'Invalid token'}), 400
        
        user.verify_email()
        
        return jsonify({'message': 'Email verified successfully'}), 200
    
    @bp.route('/me', methods=['GET'])
    @jwt_required()
    def get_current_user():
        """Get current user"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        return jsonify(user.to_dict()), 200
    
    return bp

def create_garage_blueprint():
    """Garage Finder routes"""
    bp = Blueprint('garages', __name__)
    
    @bp.route('', methods=['GET'])
    def list_garages():
        """List garages (with filters)"""
        postcode = request.args.get('postcode')
        service = request.args.get('service')
        min_rating = request.args.get('min_rating', 0, type=float)
        
        query = Garage.query.filter_by(verified=True)
        
        if postcode:
            query = query.filter_by(postcode=postcode)
        
        if service:
            query = query.filter(Garage.services.contains([service]))
        
        if min_rating:
            query = query.filter(Garage.average_rating >= min_rating)
        
        garages = query.limit(20).all()
        
        return jsonify([g.to_dict() for g in garages]), 200
    
    @bp.route('/<garage_id>', methods=['GET'])
    def get_garage(garage_id):
        """Get garage details"""
        garage = Garage.query.get(garage_id)
        if not garage:
            return jsonify({'error': 'Garage not found'}), 404
        
        return jsonify(garage.to_dict()), 200
    
    @bp.route('', methods=['POST'])
    @jwt_required()
    def create_garage():
        """Create garage (requires authentication)"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if user.user_type != 'garage':
            return jsonify({'error': 'User type must be garage'}), 403
        
        data = request.get_json()
        
        # Create organization
        org = Organization(
            owner_id=user.id,
            name=data.get('garage_name'),
            slug=data.get('garage_name', '').lower().replace(' ', '-'),
            org_type='garage',
            subscription_plan='free',
        )
        db.session.add(org)
        db.session.flush()
        
        # Create garage
        garage = Garage(
            organization_id=org.id,
            garage_name=data.get('garage_name'),
            garage_type=data.get('garage_type'),
            phone_number=data.get('phone_number'),
            email=data.get('email'),
            postcode=data.get('postcode'),
            city=data.get('city'),
            address_line_1=data.get('address_line_1'),
            services=data.get('services', ['diagnostics', 'repairs']),
        )
        db.session.add(garage)
        db.session.commit()
        
        return jsonify(garage.to_dict()), 201
    
    return bp

def create_leads_blueprint():
    """Lead management routes"""
    bp = Blueprint('leads', __name__)
    
    @bp.route('', methods=['POST'])
    @jwt_required()
    def create_lead():
        """Create a new lead"""
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Create lead
        lead = GarageLead(
            garage_id=data.get('garage_id'),
            customer_id=user_id,
            vehicle_registration=data.get('vehicle_registration'),
            issue_description=data.get('issue_description'),
            issue_category=data.get('issue_category'),
            customer_phone=data.get('customer_phone'),
            customer_email=data.get('customer_email'),
            priority=data.get('priority', 'medium'),
        )
        
        db.session.add(lead)
        db.session.commit()
        
        # Notify garage
        garage = Garage.query.get(lead.garage_id)
        send_lead_notification(garage, lead)
        
        return jsonify(lead.to_dict()), 201
    
    @bp.route('/<lead_id>', methods=['GET'])
    @jwt_required()
    def get_lead(lead_id):
        """Get lead details"""
        lead = GarageLead.query.get(lead_id)
        if not lead:
            return jsonify({'error': 'Lead not found'}), 404
        
        return jsonify(lead.to_dict()), 200
    
    @bp.route('/<lead_id>', methods=['PATCH'])
    @jwt_required()
    def update_lead(lead_id):
        """Update lead status"""
        lead = GarageLead.query.get(lead_id)
        if not lead:
            return jsonify({'error': 'Lead not found'}), 404
        
        data = request.get_json()
        
        if 'status' in data:
            lead.status = data['status']
            lead.status_updated_at = datetime.utcnow()
        
        if 'estimated_cost_low' in data:
            lead.estimated_cost_low = Decimal(str(data['estimated_cost_low']))
        
        if 'estimated_cost_high' in data:
            lead.estimated_cost_high = Decimal(str(data['estimated_cost_high']))
        
        db.session.commit()
        
        return jsonify(lead.to_dict()), 200
    
    return bp

def create_billing_blueprint():
    """Billing & Subscription routes"""
    bp = Blueprint('billing', __name__)
    
    @bp.route('/subscribe', methods=['POST'])
    @jwt_required()
    def subscribe_to_plan():
        """Subscribe organization to plan"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        data = request.get_json()
        
        org_id = data.get('organization_id')
        plan_name = data.get('plan_name')
        product_type = data.get('product_type', 'garage_finder')
        
        org = Organization.query.get(org_id)
        if not org or org.owner_id != user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get plan pricing
        plan_pricing = {
            'garage_finder': {
                'free': {'monthly': 0, 'annual': 0},
                'starter': {'monthly': 2500, 'annual': 25000},  # In pence
                'pro': {'monthly': 5000, 'annual': 50000},
                'enterprise': {'monthly': 15000, 'annual': 150000},
            },
            'recovery_network': {
                'free': {'monthly': 0, 'annual': 0},
                'standard': {'monthly': 3500, 'annual': 35000},
                'premium': {'monthly': 6000, 'annual': 60000},
            }
        }
        
        pricing = plan_pricing.get(product_type, {}).get(plan_name)
        if not pricing:
            return jsonify({'error': 'Invalid plan'}), 400
        
        monthly_price = pricing.get('monthly', 0)
        
        # Create Stripe subscription
        if monthly_price > 0:
            if not org.stripe_customer_id:
                # Create customer
                customer = stripe.Customer.create(
                    email=org.email or user.email,
                    metadata={'organization_id': str(org.id)},
                    name=org.name
                )
                org.stripe_customer_id = customer.id
                db.session.commit()
            
            try:
                # Create subscription
                subscription = stripe.Subscription.create(
                    customer=org.stripe_customer_id,
                    items=[{
                        'price_data': {
                            'currency': 'gbp',
                            'unit_amount': monthly_price,
                            'recurring': {'interval': 'month'},
                            'product_data': {'name': f'{plan_name.title()} - {product_type.replace("_", " ").title()}'}
                        }
                    }],
                    metadata={'product_type': product_type}
                )
                
                # Create subscription record
                sub = Subscription(
                    organization_id=org.id,
                    plan_name=plan_name,
                    product_type=product_type,
                    monthly_price=Decimal(str(monthly_price / 100)),
                    stripe_subscription_id=subscription.id,
                    status='active',
                    started_at=datetime.utcnow(),
                    next_billing_date=datetime.utcnow() + timedelta(days=30),
                )
                
                org.subscription_plan = plan_name
                org.subscription_status = 'active'
                org.stripe_subscription_id = subscription.id
                
                db.session.add(sub)
                db.session.commit()
                
                return jsonify({
                    'message': 'Subscription created successfully',
                    'subscription_id': subscription.id
                }), 201
                
            except stripe.error.CardError as e:
                return jsonify({'error': f'Payment failed: {e.user_message}'}), 402
        
        return jsonify({'error': 'Invalid subscription'}), 400
    
    @bp.route('/invoices', methods=['GET'])
    @jwt_required()
    def list_invoices():
        """List organization invoices"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        org_id = request.args.get('organization_id')
        
        org = Organization.query.get(org_id)
        if not org or org.owner_id != user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        invoices = Invoice.query.filter_by(organization_id=org.id).order_by(Invoice.created_at.desc()).all()
        
        return jsonify([i.to_dict() for i in invoices]), 200
    
    @bp.route('/webhook', methods=['POST'])
    def stripe_webhook():
        """Handle Stripe webhooks"""
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')
        
        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                current_app.config['STRIPE_WEBHOOK_SECRET']
            )
        except ValueError:
            return jsonify({'error': 'Invalid payload'}), 400
        except stripe.error.SignatureVerificationError:
            return jsonify({'error': 'Invalid signature'}), 400
        
        # Handle invoice.paid event
        if event['type'] == 'invoice.payment_succeeded':
            invoice_obj = event['data']['object']
            # Update invoice status
            invoice = Invoice.query.filter_by(stripe_invoice_id=invoice_obj['id']).first()
            if invoice:
                invoice.status = 'paid'
                invoice.paid_at = datetime.utcfromtimestamp(invoice_obj['paid_at'])
                invoice.paid_pence = invoice_obj['amount_paid']
                db.session.commit()
        
        # Handle subscription.deleted event
        elif event['type'] == 'customer.subscription.deleted':
            sub_obj = event['data']['object']
            subscription = Subscription.query.filter_by(stripe_subscription_id=sub_obj['id']).first()
            if subscription:
                subscription.status = 'cancelled'
                subscription.cancelled_at = datetime.utcnow()
                db.session.commit()
        
        return jsonify({'status': 'received'}), 200
    
    return bp

def create_recovery_blueprint():
    """Recovery Network routes"""
    bp = Blueprint('recovery', __name__)
    
    @bp.route('/drivers', methods=['POST'])
    @jwt_required()
    def register_driver():
        """Register recovery driver"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        data = request.get_json()
        
        # Create organization for driver
        org = Organization(
            owner_id=user.id,
            name=data.get('driver_name'),
            slug=f"driver-{user_id[:8]}",
            org_type='recovery_network',
        )
        db.session.add(org)
        db.session.flush()
        
        # Create recovery driver
        driver = RecoveryDriver(
            organization_id=org.id,
            user_id=user.id,
            driver_name=data.get('driver_name'),
            phone_number=data.get('phone_number'),
            email=data.get('email'),
            vehicle_registration=data.get('vehicle_registration'),
            vehicle_make=data.get('vehicle_make'),
            vehicle_model=data.get('vehicle_model'),
            primary_postcode_area=data.get('postcode_area'),
        )
        db.session.add(driver)
        db.session.commit()
        
        return jsonify({'message': 'Driver registered', 'driver_id': str(driver.id)}), 201
    
    @bp.route('/jobs', methods=['POST'])
    @jwt_required()
    def create_recovery_job():
        """Create recovery job"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        data = request.get_json()
        
        org_id = data.get('organization_id')
        org = Organization.query.get(org_id)
        if not org or org.owner_id != user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Generate unique job reference
        job_ref = f"REC-{datetime.utcnow().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"
        
        job = RecoveryJob(
            organization_id=org.id,
            job_reference=job_ref,
            customer_name=data.get('customer_name'),
            customer_phone=data.get('customer_phone'),
            customer_email=data.get('customer_email'),
            vehicle_registration=data.get('vehicle_registration'),
            vehicle_make=data.get('vehicle_make'),
            vehicle_model=data.get('vehicle_model'),
            incident_description=data.get('incident_description'),
            incident_type=data.get('incident_type'),
            incident_location_address=data.get('incident_location_address'),
            incident_latitude=data.get('incident_latitude'),
            incident_longitude=data.get('incident_longitude'),
            destination_address=data.get('destination_address'),
        )
        
        db.session.add(job)
        db.session.commit()
        
        return jsonify({
            'message': 'Job created',
            'job_reference': job_ref,
            'job_id': str(job.id)
        }), 201
    
    return bp

def create_admin_blueprint():
    """Admin dashboard routes"""
    bp = Blueprint('admin', __name__)
    
    @bp.route('/dashboard', methods=['GET'])
    @jwt_required()
    def admin_dashboard():
        """Admin dashboard metrics"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if user.user_type != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        # Get metrics
        total_users = db.session.query(func.count(User.id)).scalar()
        total_organizations = db.session.query(func.count(Organization.id)).scalar()
        total_garages = db.session.query(func.count(Garage.id)).scalar()
        total_leads = db.session.query(func.count(GarageLead.id)).scalar()
        
        # Revenue
        total_invoices = db.session.query(func.sum(Invoice.total_pence)).scalar() or 0
        total_revenue_gbp = total_invoices / 100
        
        # Subscriptions
        active_subscriptions = db.session.query(func.count(Subscription.id)).filter(
            Subscription.status.in_(['active', 'trialing'])
        ).scalar()
        
        return jsonify({
            'total_users': total_users,
            'total_organizations': total_organizations,
            'total_garages': total_garages,
            'total_leads': total_leads,
            'total_revenue_gbp': float(total_revenue_gbp),
            'active_subscriptions': active_subscriptions,
        }), 200
    
    @bp.route('/organizations', methods=['GET'])
    @jwt_required()
    def list_organizations():
        """List all organizations"""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if user.user_type != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        orgs = Organization.query.limit(50).all()
        
        return jsonify([o.to_dict() for o in orgs]), 200
    
    return bp

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def send_verification_email(user: User):
    """Send verification email"""
    verification_link = f"{current_app.config['FRONTEND_URL']}/verify/{user.verification_token}"
    
    msg = Message(
        subject='Verify your ApexRML email',
        recipients=[user.email],
        html=render_template('emails/verification.html', link=verification_link, name=user.first_name)
    )
    
    try:
        mail.send(msg)
    except Exception as e:
        logging.error(f'Failed to send verification email: {str(e)}')

def send_lead_notification(garage: Garage, lead: GarageLead):
    """Send lead notification to garage"""
    msg = Message(
        subject=f'New lead: {lead.issue_category}',
        recipients=[garage.email],
        html=render_template('emails/lead_notification.html', garage=garage, lead=lead)
    )
    
    try:
        mail.send(msg)
    except Exception as e:
        logging.error(f'Failed to send lead notification: {str(e)}')

def setup_logging(app):
    """Setup application logging"""
    logging.basicConfig(
        level=app.config['LOG_LEVEL'],
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def register_error_handlers(app):
    """Register error handlers"""
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        logging.error(f'Server error: {str(error)}')
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'Unauthorized'}), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': 'Forbidden'}), 403

def register_cli_commands(app):
    """Register CLI commands"""
    
    @app.cli.command()
    def create_admin():
        """Create admin user"""
        email = input('Admin email: ')
        password = input('Admin password: ')
        
        admin = User(
            email=email,
            user_type='admin',
            email_verified=True,
            status='active'
        )
        admin.set_password(password)
        
        db.session.add(admin)
        db.session.commit()
        
        print(f'Admin user {email} created successfully')
    
    @app.cli.command()
    def init_db():
        """Initialize database"""
        db.create_all()
        print('Database initialized')

# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)

# ============================================================================
# DEPLOYMENT NOTES
# ============================================================================
#
# Production deployment on Render:
#
# 1. Set environment variables:
#    - DATABASE_URL: PostgreSQL connection string (Supabase)
#    - FLASK_ENV: production
#    - SECRET_KEY: Strong random string
#    - JWT_SECRET_KEY: Strong random string
#    - STRIPE_SECRET_KEY: Live Stripe key
#    - STRIPE_WEBHOOK_SECRET: Stripe webhook signing secret
#    - SENDGRID_API_KEY: SendGrid API key
#
# 2. Procfile:
#    web: gunicorn app:app
#
# 3. requirements.txt:
#    flask==3.0.0
#    flask-sqlalchemy==3.0.5
#    flask-migrate==4.0.4
#    flask-jwt-extended==4.4.4
#    flask-cors==4.0.0
#    flask-limiter==3.5.0
#    flask-mail==0.9.1
#    stripe==5.4.0
#    psycopg2-binary==2.9.6
#    gunicorn==21.2.0
#    python-dotenv==1.0.0
#    sendgrid==6.10.0
#    requests==2.31.0
#
# 4. Database migrations:
#    flask db upgrade
#
# 5. Scale:
#    Start with 1x Render Web Service (0.5 CPU, 512MB RAM)
#    Auto-scaling to 3x when CPU > 70%
#
