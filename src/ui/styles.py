# -*- coding: utf-8 -*-
"""
Global CSS styles for the application.
"""

import streamlit as st


def apply_global_styles():
    """Apply global CSS styles to the application."""
    st.markdown("""
    <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* Global styles */
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        /* Main container */
        .main .block-container {
            padding: 2rem 3rem;
            max-width: 1400px;
        }

        /* Headers */
        h1, h2, h3 {
            font-weight: 600 !important;
            letter-spacing: -0.02em;
        }

        /* Modern button styling */
        .stButton > button {
            border-radius: 10px;
            font-weight: 500;
            padding: 0.5rem 1.5rem;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            border: none;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }

        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }

        .stButton > button[kind="secondary"] {
            background: #f8f9fa;
            color: #333;
            border: 1px solid #e0e0e0;
        }

        /* Card styling */
        .card {
            background: white;
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border: 1px solid rgba(0,0,0,0.05);
            margin-bottom: 1rem;
            transition: all 0.3s ease;
        }

        .card:hover {
            box-shadow: 0 8px 30px rgba(0,0,0,0.12);
            transform: translateY(-2px);
        }

        /* Stat card */
        .stat-card {
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
            border: 1px solid #e8e8e8;
            box-shadow: 0 2px 12px rgba(0,0,0,0.04);
        }

        .stat-value {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.25rem;
        }

        .stat-label {
            font-size: 0.85rem;
            color: #666;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        /* Board card */
        .board-card {
            background: white;
            border-radius: 12px;
            padding: 1.25rem;
            border-left: 4px solid #667eea;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            margin-bottom: 0.75rem;
            transition: all 0.2s ease;
        }

        .board-card:hover {
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        }

        .board-name {
            font-weight: 600;
            font-size: 1rem;
            color: #1a1a2e;
            margin-bottom: 0.25rem;
        }

        .board-id {
            font-size: 0.75rem;
            color: #888;
            font-family: 'Monaco', monospace;
        }

        /* Badge styles */
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }

        .badge-admin {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .badge-employee {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
        }

        .badge-active {
            background: #d4edda;
            color: #155724;
        }

        .badge-inactive {
            background: #f8d7da;
            color: #721c24;
        }

        /* User row */
        .user-row {
            display: flex;
            align-items: center;
            padding: 1rem 1.25rem;
            background: white;
            border-radius: 12px;
            margin-bottom: 0.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            border: 1px solid #f0f0f0;
            transition: all 0.2s ease;
        }

        .user-row:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            border-color: #667eea;
        }

        /* Form styling */
        [data-testid="stForm"] {
            background: #fafbfc;
            border: 1px solid #e8e8e8;
            border-radius: 16px;
            padding: 1.5rem;
        }

        /* Input styling */
        .stTextInput > div > div > input {
            border-radius: 10px;
            border: 2px solid #e8e8e8;
            padding: 0.75rem 1rem;
            transition: all 0.2s ease;
        }

        .stTextInput > div > div > input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        /* Select box */
        .stSelectbox > div > div {
            border-radius: 10px;
        }

        /* Tabs styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0;
            background: #f8f9fa;
            border-radius: 12px;
            padding: 4px;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 10px;
            padding: 12px 24px;
            font-weight: 500;
        }

        .stTabs [aria-selected="true"] {
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        /* Success message */
        .success-banner {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-weight: 500;
            box-shadow: 0 4px 15px rgba(17, 153, 142, 0.3);
        }

        /* Info box */
        .info-box {
            background: linear-gradient(135deg, #e8f4fd 0%, #f0f7ff 100%);
            border: 1px solid #b8daff;
            border-radius: 12px;
            padding: 1rem 1.25rem;
            color: #004085;
            font-size: 0.9rem;
        }

        /* Warning box */
        .warning-box {
            background: linear-gradient(135deg, #fff8e6 0%, #fffbf0 100%);
            border: 1px solid #ffc107;
            border-radius: 12px;
            padding: 1rem 1.25rem;
            color: #856404;
            font-size: 0.9rem;
        }

        /* Header with gradient */
        .gradient-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 700;
        }

        /* Divider */
        .divider {
            height: 1px;
            background: linear-gradient(90deg, transparent, #e0e0e0, transparent);
            margin: 1.5rem 0;
        }

        /* Metric cards */
        div[data-testid="stMetricValue"] {
            font-size: 2rem;
            font-weight: 700;
        }

        /* Hide default elements */
        .css-15zrgzn {display: none}
        .css-zt5igj {display: none}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}

        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        }

        [data-testid="stSidebar"] .stMarkdown {
            color: rgba(255,255,255,0.9);
        }

        [data-testid="stSidebar"] .stButton > button {
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            color: white;
        }

        [data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(255,255,255,0.2);
        }

        /* Multiselect */
        .stMultiSelect > div {
            border-radius: 10px;
        }

        /* Progress indicator */
        .step-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            border-radius: 25px;
            font-weight: 500;
            font-size: 0.85rem;
        }

        .step-active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .step-complete {
            background: #d4edda;
            color: #155724;
        }

        .step-pending {
            background: #f8f9fa;
            color: #6c757d;
        }
    </style>
    """, unsafe_allow_html=True)


def apply_login_styles():
    """Apply additional styles for login page."""
    st.markdown("""
    <style>
        /* Hide sidebar on login page */
        [data-testid="stSidebar"] {
            display: none;
        }

        /* Login page background */
        .login-bg {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f64f59 100%);
            z-index: -1;
        }

        /* Glass card effect */
        .glass-card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 3rem;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            border: 1px solid rgba(255, 255, 255, 0.3);
        }

        /* Logo animation */
        .logo-container {
            width: 100px;
            height: 100px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 1.5rem;
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.4);
            animation: float 3s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }

        .logo-icon {
            font-size: 3rem;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
        }

        /* Title styling */
        .login-title {
            font-size: 2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #1a1a2e 0%, #667eea 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            margin-bottom: 0.5rem;
            letter-spacing: -0.03em;
        }

        .login-subtitle {
            color: #666;
            text-align: center;
            font-size: 1rem;
            margin-bottom: 2rem;
        }

        /* Input label styling */
        .input-label {
            font-size: 0.85rem;
            font-weight: 600;
            color: #374151;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        /* Feature list */
        .feature-item {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem;
            background: linear-gradient(135deg, #f8f9fa 0%, #fff 100%);
            border-radius: 12px;
            margin-bottom: 0.5rem;
            border: 1px solid #e8e8e8;
        }

        .feature-icon {
            width: 36px;
            height: 36px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1rem;
        }

        .feature-text {
            font-size: 0.9rem;
            color: #374151;
            font-weight: 500;
        }

        /* Footer hint */
        .login-hint {
            background: linear-gradient(135deg, #fef3c7 0%, #fef9c3 100%);
            border: 1px solid #fbbf24;
            border-radius: 12px;
            padding: 1rem;
            margin-top: 1.5rem;
            text-align: center;
        }

        .login-hint-title {
            font-size: 0.75rem;
            font-weight: 600;
            color: #92400e;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }

        .login-hint-content {
            font-size: 0.85rem;
            color: #78350f;
        }

        .login-hint code {
            background: rgba(146, 64, 14, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)
