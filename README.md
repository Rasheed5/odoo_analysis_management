# Analysis Management Odoo Module

[![Odoo Version](https://img.shields.io/badge/Odoo-18.0-714B67.svg)](https://www.odoo.com/)
[![License](https://img.shields.io/badge/License-LGPL--3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0-standalone.html)

A professional, comprehensive Odoo 18 module designed for **Business and Systems Analysis** departments. This module streamlines the entire lifecycle of analysis work, from intake to deliverable approval, while providing managers with real-time strategic insights.

## 🚀 Key Features

### 📊 Strategic Dashboard
- **Interactive Analytics**: Visual distribution of Workload by Request Type and Monthly Velocity trends using Chart.js.
- **KPI Cockpit**: Real-time tracking of Open Requests, Overdue Deliverables, and Pending Approvals.
- **Personal Highlights**: A dedicated section for analysts to track their specific Active Requests, Action Items, and Meetings.

### 🔄 Change Management (CR)
- **Lifecycle Governance**: Dedicated workflow for handling Change Requests.
- **Financial Impact**: Track estimated costs and financial implications of changes.
- **Bilingual Reporting**: High-quality PDF report generation in both **Arabic** and **English**, perfect for executive review.

### 📝 Operational Tracking
- **Requirement Management**: Breakdown of business, functional, and technical requirements.
- **Deliverable Oversight**: Milestone tracking and formal approval workflows for analysis artifacts.
- **Meeting Management**: Integrated tracking of minutes and participant attendance.
- **Action Items**: Centralized task management for blockers and next steps.

## 🛠 Installation

1. Clone this repository into your Odoo `custom_addons` directory:
   ```bash
   git clone https://github.com/YOUR_USERNAME/odoo_analysis_management.git
   ```
2. Ensure you have the following dependencies installed in your Odoo instance:
   - `mail`
   - `project`
3. Update your Odoo App List and search for "Analysis Management".
4. Click **Activate**.

## 🖥 Configuration

- **User Roles**: The module includes three security groups:
  - **Analysis User (Analyst)**: Can create and manage their assigned requests and deliverables.
  - **Analysis Reviewer**: Provides formal review and feedback on analysis artifacts.
  - **Analysis Manager**: Full administrative access, including dashboard oversight and high-level approvals.

---

**Author**: Rasheed Ali Al-Dhaferi  
**Category**: Operations/Analysis  
**Version**: 18.0.1.0.0
