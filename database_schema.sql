-- ============================================================================
-- ApexRML SaaS: PostgreSQL Database Schema
-- Database: apexrml_production
-- Version: 1.0.0
-- Platform: Supabase (PostgreSQL 14+)
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "hstore";

-- ============================================================================
-- TABLE 1: USERS (Core Authentication)
-- ============================================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(500) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone_number VARCHAR(20),
    user_type VARCHAR(50) NOT NULL CHECK (user_type IN ('customer', 'garage', 'recovery_driver', 'admin')),
    
    -- Authentication
    email_verified BOOLEAN DEFAULT FALSE,
    email_verified_at TIMESTAMP,
    verification_token VARCHAR(500),
    
    -- OAuth2 Integration
    oauth_provider VARCHAR(50),
    oauth_id VARCHAR(500),
    oauth_token VARCHAR(1000),
    
    -- Account Status
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'suspended', 'deleted')),
    last_login_at TIMESTAMP,
    login_count INT DEFAULT 0,
    
    -- Metadata
    avatar_url TEXT,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    
    INDEX idx_email (email),
    INDEX idx_user_type (user_type),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at DESC)
);

-- ============================================================================
-- TABLE 2: ORGANIZATIONS (Multi-tenant Support)
-- ============================================================================
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    
    -- Basic Info
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    website VARCHAR(255),
    phone_number VARCHAR(20),
    email VARCHAR(255),
    
    -- Organization Type
    org_type VARCHAR(50) NOT NULL CHECK (org_type IN ('garage', 'recovery_network', 'fleet_manager', 'parts_supplier')),
    
    -- Address
    address_line_1 VARCHAR(255),
    address_line_2 VARCHAR(255),
    city VARCHAR(100),
    postcode VARCHAR(20),
    country_code VARCHAR(2) DEFAULT 'GB',
    
    -- Business Details
    company_registration VARCHAR(50),
    vat_number VARCHAR(50),
    business_type VARCHAR(100),
    employees_count INT,
    
    -- Branding
    logo_url TEXT,
    banner_url TEXT,
    brand_color VARCHAR(10),
    
    -- Subscription Details (Garage Finder / Recovery Network)
    subscription_plan VARCHAR(50) DEFAULT 'free' CHECK (subscription_plan IN ('free', 'starter', 'pro', 'enterprise')),
    subscription_status VARCHAR(50) DEFAULT 'active' CHECK (subscription_status IN ('active', 'cancelled', 'expired', 'past_due')),
    subscription_started_at TIMESTAMP,
    subscription_ends_at TIMESTAMP,
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    
    -- Billing
    billing_email VARCHAR(255),
    billing_address_same BOOLEAN DEFAULT TRUE,
    billing_address_line_1 VARCHAR(255),
    billing_address_line_2 VARCHAR(255),
    billing_city VARCHAR(100),
    billing_postcode VARCHAR(20),
    
    -- Account Status
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'cancelled')),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_owner_id (owner_id),
    INDEX idx_slug (slug),
    INDEX idx_org_type (org_type),
    INDEX idx_subscription_status (subscription_status)
);

-- ============================================================================
-- TABLE 3: ORGANIZATION MEMBERS
-- ============================================================================
CREATE TABLE organization_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Role & Permissions
    role VARCHAR(50) NOT NULL CHECK (role IN ('owner', 'admin', 'manager', 'member', 'viewer')),
    permissions JSONB DEFAULT '["read"]',
    
    -- Status
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'invited', 'inactive')),
    invited_at TIMESTAMP,
    joined_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(organization_id, user_id),
    INDEX idx_organization_id (organization_id),
    INDEX idx_user_id (user_id),
    INDEX idx_role (role)
);

-- ============================================================================
-- TABLE 4: GARAGES (Garage Finder - B2B SaaS)
-- ============================================================================
CREATE TABLE garages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Basic Info
    garage_name VARCHAR(255) NOT NULL,
    garage_type VARCHAR(100) CHECK (garage_type IN ('independent', 'mot_station', 'quick_fit', 'dealership', 'specialist')),
    
    -- Contact
    phone_number VARCHAR(20) NOT NULL,
    email VARCHAR(255) NOT NULL,
    
    -- Address
    address_line_1 VARCHAR(255),
    address_line_2 VARCHAR(255),
    city VARCHAR(100),
    postcode VARCHAR(20),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    
    -- Services
    services JSONB DEFAULT '["diagnostics", "repairs", "maintenance"]',
    vehicle_brands TEXT[], -- List of car brands serviced
    equipment_list JSONB, -- Specialist equipment
    
    -- Capacity
    bays_available INT,
    technicians_count INT,
    
    -- Ratings & Reviews
    average_rating DECIMAL(3, 2) DEFAULT 0,
    total_reviews INT DEFAULT 0,
    response_time_hours INT DEFAULT 24,
    
    -- Certifications
    mot_license_number VARCHAR(50),
    ase_certified BOOLEAN DEFAULT FALSE,
    certifications JSONB DEFAULT '[]',
    
    -- Operating Hours
    operating_hours JSONB DEFAULT '{"mon": {"open": "08:00", "close": "17:00"}}',
    
    -- Pricing Strategy
    labour_rate_per_hour DECIMAL(8, 2),
    warranty_offered INT, -- In months
    
    -- Features
    online_booking_enabled BOOLEAN DEFAULT FALSE,
    accepts_walkins BOOLEAN DEFAULT TRUE,
    mobile_service_available BOOLEAN DEFAULT FALSE,
    
    -- Lead Management
    leads_received INT DEFAULT 0,
    leads_converted INT DEFAULT 0,
    conversion_rate DECIMAL(5, 2) DEFAULT 0,
    
    -- Metrics
    total_jobs_completed INT DEFAULT 0,
    average_job_value DECIMAL(8, 2),
    
    -- Status
    verified BOOLEAN DEFAULT FALSE,
    verification_date TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_organization_id (organization_id),
    INDEX idx_postcode (postcode),
    INDEX idx_average_rating (average_rating DESC),
    INDEX idx_coordinates (latitude, longitude)
);

-- ============================================================================
-- TABLE 5: GARAGE LEADS (Lead Management)
-- ============================================================================
CREATE TABLE garage_leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    garage_id UUID NOT NULL REFERENCES garages(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Lead Details
    vehicle_registration VARCHAR(10),
    vehicle_make VARCHAR(50),
    vehicle_model VARCHAR(50),
    vehicle_year INT,
    
    -- Issue Description
    issue_description TEXT NOT NULL,
    issue_category VARCHAR(100),
    priority VARCHAR(20) CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    
    -- Lead Status
    status VARCHAR(50) DEFAULT 'new' CHECK (status IN ('new', 'contacted', 'quoted', 'accepted', 'declined', 'completed')),
    status_updated_at TIMESTAMP,
    
    -- Pricing
    estimated_cost_low DECIMAL(8, 2),
    estimated_cost_high DECIMAL(8, 2),
    final_cost DECIMAL(8, 2),
    
    -- Timeline
    preferred_date_from DATE,
    preferred_date_to DATE,
    estimated_duration_hours INT,
    actual_duration_hours INT,
    
    -- Feedback
    customer_rating INT CHECK (customer_rating >= 1 AND customer_rating <= 5),
    customer_feedback TEXT,
    garage_notes TEXT,
    
    -- Contact Info
    customer_phone VARCHAR(20),
    customer_email VARCHAR(255),
    preferred_contact_method VARCHAR(20) CHECK (preferred_contact_method IN ('phone', 'email', 'sms')),
    
    -- Source
    lead_source VARCHAR(50) DEFAULT 'apexrml' CHECK (lead_source IN ('apexrml', 'direct', 'referral')),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_garage_id (garage_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at DESC),
    INDEX idx_priority (priority)
);

-- ============================================================================
-- TABLE 6: RECOVERY NETWORK (B2B SaaS)
-- ============================================================================
CREATE TABLE recovery_drivers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Driver Info
    driver_name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    
    -- License & Certifications
    driving_license_number VARCHAR(50),
    driving_license_type VARCHAR(20), -- LGV, HGV etc
    medical_expiry_date DATE,
    cpc_expiry_date DATE,
    
    -- Vehicle Details
    vehicle_registration VARCHAR(10),
    vehicle_make VARCHAR(50),
    vehicle_model VARCHAR(50),
    vehicle_capacity_tonnes DECIMAL(5, 2),
    equipment_type JSONB DEFAULT '["wheel_lift", "flatbed", "tow_bar"]',
    
    -- Geographic Area
    primary_postcode_area VARCHAR(10),
    service_radius_miles INT DEFAULT 30,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    
    -- Availability
    status VARCHAR(50) DEFAULT 'inactive' CHECK (status IN ('active', 'inactive', 'on_break', 'unavailable')),
    currently_available BOOLEAN DEFAULT FALSE,
    on_duty_from TIMESTAMP,
    on_duty_until TIMESTAMP,
    
    -- Performance
    jobs_completed INT DEFAULT 0,
    average_response_time_minutes INT,
    customer_rating DECIMAL(3, 2),
    total_revenue DECIMAL(10, 2) DEFAULT 0,
    
    -- Insurance
    insurance_provider VARCHAR(100),
    policy_number VARCHAR(100),
    insurance_expires_at DATE,
    
    -- Verification
    background_check_completed BOOLEAN DEFAULT FALSE,
    background_check_date DATE,
    verified_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_organization_id (organization_id),
    INDEX idx_status (status),
    INDEX idx_coordinates (latitude, longitude),
    INDEX idx_primary_postcode (primary_postcode_area)
);

-- ============================================================================
-- TABLE 7: RECOVERY JOBS
-- ============================================================================
CREATE TABLE recovery_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    driver_id UUID REFERENCES recovery_drivers(id) ON DELETE SET NULL,
    
    -- Job Details
    job_reference VARCHAR(50) UNIQUE NOT NULL,
    customer_name VARCHAR(255),
    customer_phone VARCHAR(20),
    customer_email VARCHAR(255),
    
    -- Vehicle Details
    vehicle_registration VARCHAR(10),
    vehicle_make VARCHAR(50),
    vehicle_model VARCHAR(50),
    vehicle_color VARCHAR(50),
    
    -- Incident Details
    incident_description TEXT,
    incident_type VARCHAR(50) CHECK (incident_type IN ('breakdown', 'accident', 'storage', 'transportation', 'other')),
    incident_location_address TEXT,
    incident_latitude DECIMAL(10, 8),
    incident_longitude DECIMAL(11, 8),
    
    -- Destination
    destination_address TEXT,
    destination_latitude DECIMAL(10, 8),
    destination_longitude DECIMAL(11, 8),
    
    -- Timeline
    incident_date_time TIMESTAMP,
    job_created_at TIMESTAMP,
    job_assigned_at TIMESTAMP,
    job_started_at TIMESTAMP,
    job_completed_at TIMESTAMP,
    estimated_completion_time TIMESTAMP,
    
    -- Status
    job_status VARCHAR(50) DEFAULT 'pending' CHECK (job_status IN ('pending', 'assigned', 'en_route', 'on_scene', 'in_progress', 'completed', 'cancelled')),
    
    -- Pricing
    mileage_km DECIMAL(8, 2),
    distance_charge DECIMAL(8, 2),
    call_out_charge DECIMAL(8, 2),
    additional_charges DECIMAL(8, 2),
    total_cost DECIMAL(10, 2),
    
    -- Insurance
    claim_reference VARCHAR(50),
    insurance_company VARCHAR(100),
    insured_recovery BOOLEAN DEFAULT FALSE,
    
    -- Notes
    driver_notes TEXT,
    support_notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_organization_id (organization_id),
    INDEX idx_driver_id (driver_id),
    INDEX idx_job_status (job_status),
    INDEX idx_job_reference (job_reference),
    INDEX idx_job_created_at (job_created_at DESC)
);

-- ============================================================================
-- TABLE 8: PARTS (Parts Finder - Affiliate Model)
-- ============================================================================
CREATE TABLE parts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Part Details
    part_name VARCHAR(500) NOT NULL,
    part_number VARCHAR(100) UNIQUE,
    oem_number VARCHAR(100),
    description TEXT,
    
    -- Categorization
    part_category VARCHAR(100),
    sub_category VARCHAR(100),
    vehicle_application TEXT, -- JSON array of {make, model, year}
    
    -- Specifications
    manufacturer VARCHAR(100),
    brand VARCHAR(100),
    condition VARCHAR(50) CHECK (condition IN ('new', 'refurbished', 'used')),
    warranty_months INT,
    
    -- Sourcing
    suppliers JSONB DEFAULT '[]', -- {source: "ebay", "gsf", "awin", price: 0.00, affiliate_url: ""}
    
    -- Pricing (ApexRML markup applied on frontend)
    cost_price DECIMAL(10, 2),
    retail_price DECIMAL(10, 2),
    min_price DECIMAL(10, 2),
    max_price DECIMAL(10, 2),
    commission_rate DECIMAL(5, 2) DEFAULT 25, -- Percentage
    
    -- Images
    image_urls TEXT[],
    
    -- Metadata
    search_keywords TEXT,
    popularity_score INT DEFAULT 0,
    conversion_rate DECIMAL(5, 2),
    
    -- Inventory (GSF sync)
    stock_level INT DEFAULT 0,
    warehouse_location VARCHAR(100),
    lead_time_days INT,
    
    -- Status
    active BOOLEAN DEFAULT TRUE,
    last_updated TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_part_number (part_number),
    INDEX idx_part_category (part_category),
    INDEX idx_active (active),
    INDEX idx_popularity (popularity_score DESC)
);

-- ============================================================================
-- TABLE 9: AI DIAGNOSTICS (Premium Feature)
-- ============================================================================
CREATE TABLE diagnostics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    garage_id UUID REFERENCES garages(id) ON DELETE SET NULL,
    
    -- Vehicle
    vehicle_registration VARCHAR(10),
    vehicle_make VARCHAR(50),
    vehicle_model VARCHAR(50),
    vehicle_year INT,
    vehicle_mileage INT,
    
    -- Symptom Input
    symptom_description TEXT NOT NULL,
    symptom_category VARCHAR(100),
    issue_severity VARCHAR(20) CHECK (issue_severity IN ('minor', 'moderate', 'severe', 'critical')),
    issue_duration TEXT, -- "2 days", "2 weeks" etc
    
    -- AI Analysis
    ai_diagnosis TEXT,
    possible_fault_codes JSONB, -- [{code: "P0101", name: "...", probability: 0.95}]
    recommended_parts JSONB, -- [{part_id: uuid, name: "...", priority: 1, reason: "..."}]
    estimated_repair_cost_low DECIMAL(8, 2),
    estimated_repair_cost_high DECIMAL(8, 2),
    
    -- Confidence Scores
    confidence_score DECIMAL(5, 2), -- 0-100
    requires_professional_inspection BOOLEAN DEFAULT FALSE,
    
    -- Action Taken
    quote_generated BOOLEAN DEFAULT FALSE,
    quote_id UUID REFERENCES garage_leads(id) ON DELETE SET NULL,
    
    -- Subscription
    is_premium BOOLEAN DEFAULT FALSE,
    subscription_used_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_user_id (user_id),
    INDEX idx_garage_id (garage_id),
    INDEX idx_vehicle_registration (vehicle_registration),
    INDEX idx_created_at (created_at DESC)
);

-- ============================================================================
-- TABLE 10: SUBSCRIPTIONS & BILLING
-- ============================================================================
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Subscription Details
    plan_name VARCHAR(50) NOT NULL CHECK (plan_name IN ('free', 'starter', 'pro', 'enterprise')),
    product_type VARCHAR(50) NOT NULL CHECK (product_type IN ('garage_finder', 'recovery_network', 'ai_diagnostics')),
    
    -- Pricing
    monthly_price DECIMAL(8, 2),
    annual_price DECIMAL(8, 2),
    billing_cycle VARCHAR(20) CHECK (billing_cycle IN ('monthly', 'annual')),
    
    -- Stripe Integration
    stripe_subscription_id VARCHAR(255),
    stripe_price_id VARCHAR(255),
    
    -- Status
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'trialing', 'past_due', 'cancelled', 'expired')),
    trial_ends_at TIMESTAMP,
    started_at TIMESTAMP,
    ends_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    
    -- Auto-Renewal
    auto_renew BOOLEAN DEFAULT TRUE,
    next_billing_date DATE,
    
    -- Features & Limits
    features JSONB DEFAULT '{}', -- {leads_per_month: 10, users: 3, etc}
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_organization_id (organization_id),
    INDEX idx_status (status),
    INDEX idx_next_billing_date (next_billing_date)
);

-- ============================================================================
-- TABLE 11: INVOICES & PAYMENTS
-- ============================================================================
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
    
    -- Invoice Details
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    stripe_invoice_id VARCHAR(255),
    
    -- Amounts (in GBP pence - stored as integers)
    subtotal_pence INT, -- £25.00 = 2500
    tax_pence INT,
    total_pence INT,
    paid_pence INT DEFAULT 0,
    
    -- Status
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'issued', 'paid', 'overdue', 'cancelled')),
    issued_at TIMESTAMP,
    due_date DATE,
    paid_at TIMESTAMP,
    
    -- Payment Method
    payment_method VARCHAR(50), -- card, bank_transfer, direct_debit
    
    -- Items
    line_items JSONB DEFAULT '[]', -- {description, quantity, unit_price, amount}
    
    -- Notes
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_organization_id (organization_id),
    INDEX idx_status (status),
    INDEX idx_invoice_number (invoice_number),
    INDEX idx_due_date (due_date)
);

-- ============================================================================
-- TABLE 12: REVIEWS & RATINGS
-- ============================================================================
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    garage_id UUID NOT NULL REFERENCES garages(id) ON DELETE CASCADE,
    reviewer_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES garage_leads(id) ON DELETE SET NULL,
    
    -- Rating
    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(255),
    comment TEXT,
    
    -- Review Categories
    quality_of_work INT CHECK (quality_of_work >= 1 AND quality_of_work <= 5),
    communication INT CHECK (communication >= 1 AND communication <= 5),
    price_value INT CHECK (price_value >= 1 AND price_value <= 5),
    responsiveness INT CHECK (responsiveness >= 1 AND responsiveness <= 5),
    
    -- Moderation
    verified_purchase BOOLEAN DEFAULT TRUE,
    helpful_votes INT DEFAULT 0,
    unhelpful_votes INT DEFAULT 0,
    reported BOOLEAN DEFAULT FALSE,
    approved BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_garage_id (garage_id),
    INDEX idx_reviewer_id (reviewer_id),
    INDEX idx_rating (rating),
    INDEX idx_created_at (created_at DESC)
);

-- ============================================================================
-- TABLE 13: AFFILIATE TRANSACTIONS (Parts Finder Revenue)
-- ============================================================================
CREATE TABLE affiliate_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    part_id UUID REFERENCES parts(id) ON DELETE SET NULL,
    
    -- Transaction Details
    transaction_type VARCHAR(50) CHECK (transaction_type IN ('click', 'impression', 'conversion', 'commission')),
    affiliate_network VARCHAR(50) CHECK (affiliate_network IN ('ebay_epn', 'awin', 'gsf', 'other')),
    
    -- Amounts (in pence)
    commission_amount_pence INT,
    order_value_pence INT,
    
    -- Details
    affiliate_ref_id VARCHAR(255),
    tracking_id VARCHAR(255),
    external_order_id VARCHAR(255),
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'paid', 'failed')),
    confirmed_at TIMESTAMP,
    paid_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_affiliate_network (affiliate_network),
    INDEX idx_created_at (created_at DESC)
);

-- ============================================================================
-- TABLE 14: AUDIT LOG (Security & Compliance)
-- ============================================================================
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    
    -- Action Details
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50), -- 'user', 'garage', 'lead', 'subscription'
    resource_id UUID,
    
    -- Changes
    changes JSONB DEFAULT '{}', -- Before/after values
    
    -- Metadata
    ip_address VARCHAR(45),
    user_agent TEXT,
    status_code INT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_user_id (user_id),
    INDEX idx_organization_id (organization_id),
    INDEX idx_resource_type (resource_type),
    INDEX idx_created_at (created_at DESC)
);

-- ============================================================================
-- TABLE 15: API KEYS (For 3rd Party Integration)
-- ============================================================================
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Key Details
    key_name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(500) NOT NULL,
    key_prefix VARCHAR(20) NOT NULL, -- First 8 chars for display
    
    -- Permissions
    scopes JSONB DEFAULT '["read"]',
    rate_limit_per_minute INT DEFAULT 100,
    
    -- Usage
    last_used_at TIMESTAMP,
    total_requests INT DEFAULT 0,
    
    -- Status
    active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_organization_id (organization_id),
    INDEX idx_key_hash (key_hash),
    INDEX idx_active (active)
);

-- ============================================================================
-- TABLE 16: NOTIFICATIONS
-- ============================================================================
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Notification Details
    type VARCHAR(50) NOT NULL, -- 'lead_received', 'job_assigned', 'payment_received', etc
    title VARCHAR(255),
    message TEXT,
    action_url VARCHAR(500),
    
    -- Status
    read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    
    -- Preferences
    channel VARCHAR(50) DEFAULT 'in_app' CHECK (channel IN ('in_app', 'email', 'sms', 'push')),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_user_id (user_id),
    INDEX idx_read (read),
    INDEX idx_created_at (created_at DESC)
);

-- ============================================================================
-- VIEWS (Business Intelligence)
-- ============================================================================

-- Dashboard: Garage Performance
CREATE VIEW garage_performance_view AS
SELECT 
    g.id,
    g.garage_name,
    o.name AS organization_name,
    COUNT(DISTINCT gl.id) AS total_leads,
    COUNT(DISTINCT CASE WHEN gl.status = 'converted' THEN gl.id END) AS converted_leads,
    ROUND((COUNT(DISTINCT CASE WHEN gl.status = 'converted' THEN gl.id END)::NUMERIC / 
           NULLIF(COUNT(DISTINCT gl.id), 0) * 100), 2) AS conversion_rate,
    AVG(gl.final_cost)::NUMERIC(10,2) AS avg_job_value,
    g.average_rating,
    COUNT(DISTINCT r.id) AS total_reviews,
    DATE_TRUNC('month', CURRENT_DATE) AS reporting_month
FROM garages g
LEFT JOIN organizations o ON g.organization_id = o.id
LEFT JOIN garage_leads gl ON g.id = gl.garage_id
LEFT JOIN reviews r ON g.id = r.garage_id
GROUP BY g.id, g.garage_name, o.name;

-- Dashboard: Revenue Summary
CREATE VIEW revenue_summary_view AS
SELECT 
    DATE_TRUNC('month', i.created_at)::DATE AS month,
    SUM(i.total_pence)::NUMERIC(12,2) / 100 AS total_revenue_gbp,
    COUNT(DISTINCT i.id) AS total_invoices,
    COUNT(DISTINCT i.organization_id) AS unique_customers,
    SUM(CASE WHEN i.status = 'paid' THEN i.total_pence ELSE 0 END)::NUMERIC(12,2) / 100 AS paid_revenue_gbp
FROM invoices i
GROUP BY DATE_TRUNC('month', i.created_at);

-- Dashboard: Subscription Metrics
CREATE VIEW subscription_metrics_view AS
SELECT 
    s.plan_name,
    s.product_type,
    COUNT(DISTINCT s.id) AS active_subscriptions,
    SUM(s.monthly_price)::NUMERIC(12,2) AS mrr_gbp,
    COUNT(DISTINCT CASE WHEN s.status = 'trialing' THEN s.id END) AS trialing_count,
    COUNT(DISTINCT CASE WHEN s.status = 'cancelled' THEN s.id END) AS cancelled_count
FROM subscriptions s
WHERE s.status IN ('active', 'trialing')
GROUP BY s.plan_name, s.product_type;

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Composite indexes for common queries
CREATE INDEX idx_garage_leads_garage_status ON garage_leads(garage_id, status);
CREATE INDEX idx_garage_leads_date_status ON garage_leads(created_at DESC, status);
CREATE INDEX idx_recovery_jobs_driver_status ON recovery_jobs(driver_id, job_status);
CREATE INDEX idx_subscriptions_org_status ON subscriptions(organization_id, status);
CREATE INDEX idx_organization_members_org_user ON organization_members(organization_id, user_id);
CREATE INDEX idx_invoices_org_status_date ON invoices(organization_id, status, issued_at DESC);
CREATE INDEX idx_diagnostics_user_created ON diagnostics(user_id, created_at DESC);
CREATE INDEX idx_reviews_garage_rating ON reviews(garage_id, rating DESC);
CREATE INDEX idx_parts_category_active ON parts(part_category, active);

-- Full-text search indexes
CREATE INDEX idx_garage_name_search ON garages USING GIN(to_tsvector('english', garage_name));
CREATE INDEX idx_part_name_search ON parts USING GIN(to_tsvector('english', part_name));

-- ============================================================================
-- TRIGGERS & FUNCTIONS
-- ============================================================================

-- Update timestamp on every modification
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all timestamped tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_garages_updated_at BEFORE UPDATE ON garages FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Calculate garage average rating when review added/updated
CREATE OR REPLACE FUNCTION update_garage_rating()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE garages 
    SET average_rating = (
        SELECT AVG(rating) FROM reviews WHERE garage_id = NEW.garage_id AND approved = TRUE
    ),
    total_reviews = (
        SELECT COUNT(*) FROM reviews WHERE garage_id = NEW.garage_id AND approved = TRUE
    )
    WHERE id = NEW.garage_id;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_garage_rating_trigger AFTER INSERT OR UPDATE ON reviews 
FOR EACH ROW EXECUTE FUNCTION update_garage_rating();

-- ============================================================================
-- INITIAL DATA SETUP
-- ============================================================================

-- Insert subscription plan templates
INSERT INTO subscriptions (id, organization_id, plan_name, product_type, monthly_price, billing_cycle, status, started_at)
VALUES 
    (uuid_generate_v4(), null, 'free', 'garage_finder', 0, 'monthly', 'active', CURRENT_TIMESTAMP),
    (uuid_generate_v4(), null, 'starter', 'garage_finder', 25.00, 'monthly', 'active', CURRENT_TIMESTAMP),
    (uuid_generate_v4(), null, 'pro', 'garage_finder', 50.00, 'monthly', 'active', CURRENT_TIMESTAMP),
    (uuid_generate_v4(), null, 'enterprise', 'garage_finder', 150.00, 'monthly', 'active', CURRENT_TIMESTAMP),
    (uuid_generate_v4(), null, 'free', 'recovery_network', 0, 'monthly', 'active', CURRENT_TIMESTAMP),
    (uuid_generate_v4(), null, 'standard', 'recovery_network', 35.00, 'monthly', 'active', CURRENT_TIMESTAMP),
    (uuid_generate_v4(), null, 'premium', 'recovery_network', 60.00, 'monthly', 'active', CURRENT_TIMESTAMP),
    (uuid_generate_v4(), null, 'free', 'ai_diagnostics', 0, 'monthly', 'active', CURRENT_TIMESTAMP),
    (uuid_generate_v4(), null, 'premium', 'ai_diagnostics', 15.00, 'monthly', 'active', CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
-- 
-- Version History:
-- 1.0.0 - Initial schema design with multi-tenant support, SaaS billing, audit logging
--
-- Notes:
-- - All timestamps are in UTC
-- - All monetary values stored in GBP
-- - Multi-tenancy achieved via organization_id foreign keys
-- - Stripe IDs stored for webhook processing
-- - JSONB columns allow flexible metadata storage
-- - Full-text search on garage/part names
-- - Comprehensive audit logging for compliance
--
-- To deploy on Supabase:
-- 1. Create new project on Supabase
-- 2. Connect to PostgreSQL database via psql CLI
-- 3. Run: psql -h db.XXXX.supabase.co -U postgres -d postgres -f database_schema.sql
-- 4. Enable Row-Level Security (RLS) for multi-tenancy
-- 5. Create RLS policies for each table
--
