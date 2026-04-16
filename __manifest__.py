# -*- coding: utf-8 -*-
{
    'name': "Analysis Management",

    'summary': "Manage Systems and Business Analysis Department",

    'description': """
Core module for managing business analysis requests, tracking status, and overseeing team performance.
    """,

    'author': "Rasheed Ali Al-Dhaferi",
    'category': 'Operations/Analysis',
    'version': '18.0.1.1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'project'],

    # always loaded
    'data': [
        'security/security.xml',
        'data/analysis_request_sequence.xml',
        'data/analysis_meeting_sequence.xml',
        'data/analysis_action_item_sequence.xml',
        'data/analysis_requirement_sequence.xml',
        'data/analysis_deliverable_sequence.xml',
        'data/analysis_change_request_sequence.xml',
        'views/analysis_dashboard_views.xml',
        'views/analysis_request_views.xml',
        'views/analysis_daily_log_views.xml',
        'views/analysis_meeting_views.xml',
        'views/analysis_action_item_views.xml',
        'views/analysis_requirement_views.xml',
        'views/analysis_deliverable_views.xml',
        'views/analysis_change_request_views.xml',
        'views/analysis_change_request_report.xml',
        'views/analysis_tag_views.xml',
        'views/analysis_menu.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'analysis_management/static/src/components/dashboard/dashboard.js',
            'analysis_management/static/src/components/dashboard/dashboard.xml',
            'analysis_management/static/src/components/dashboard/dashboard.scss',
        ],
    },
    # only loaded in demonstration mode
    'demo': [],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
