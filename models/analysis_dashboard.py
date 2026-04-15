from odoo import models, api, fields, _
from datetime import date, timedelta

class AnalysisDashboard(models.AbstractModel):
    """
    Dashboard Aggregation Engine:
    This model does not store data. Instead, it computes real-time metrics
    by querying all analysis models. It serves as the backend for the
    OWL-based Analysis Dashboard.
    """
    _name = 'analysis.dashboard'
    _description = 'Analysis Management Dashboard'

    @api.model
    def get_dashboard_data(self):
        """Aggregate all metrics for the Analysis Management Dashboard"""
        user = self.env.user
        today = date.today()
        seven_days_later = today + timedelta(days=7)

        # 1. Top KPI Summary Cards
        # Requests
        open_requests = self.env['analysis.request'].search([('state', 'not in', ['completed', 'closed', 'rejected'])])
        overdue_requests = open_requests.filtered(lambda r: r.due_date and r.due_date < today)
        pending_review_requests = self.env['analysis.request'].search_count([('state', '=', 'pending_review')])

        # Action Items
        open_action_items = self.env['analysis.action.item'].search([('state', '=', 'open')])
        overdue_action_items = self.env['analysis.action.item'].search_count([('is_overdue', '=', True)])

        # Deliverables
        approved_deliverables = self.env['analysis.deliverable'].search_count([('state', '=', 'approved')])
        pending_review_deliverables = self.env['analysis.deliverable'].search_count([('state', '=', 'pending_review')])

        # Meetings
        meetings_today = self.env['analysis.meeting'].search_count([
            ('meeting_datetime', '>=', today),
            ('meeting_datetime', '<', today + timedelta(days=1))
        ])

        # 2. Request Pipeline / Workflow Overview
        states = ['new', 'under_review', 'approved', 'assigned', 'in_progress', 'waiting_business', 'waiting_technical', 'pending_review', 'completed', 'closed', 'rejected']
        pipeline_data = []
        for state in states:
            count = self.env['analysis.request'].search_count([('state', '=', state)])
            pipeline_data.append({
                'state': state,
                'label': dict(self.env['analysis.request']._fields['state'].selection).get(state),
                'count': count
            })

        # 3. Analyst Workload Overview
        analysts = self.env['res.users'].search([('groups_id', 'in', self.env.ref('analysis_management.group_analysis_user').id)])
        workload_data = []
        for analyst in analysts:
            workload_data.append({
                'id': analyst.id,
                'name': analyst.name,
                'requests': self.env['analysis.request'].search_count([('analyst_ids', 'in', analyst.id), ('state', '!=', 'completed')]),
                'action_items': self.env['analysis.action.item'].search_count([('owner_id', '=', analyst.id), ('state', '!=', 'done')]),
                'overdue': self.env['analysis.action.item'].search_count([('owner_id', '=', analyst.id), ('is_overdue', '=', True)]),
                'deliverables': self.env['analysis.deliverable'].search_count([('analyst_ids', 'in', analyst.id), ('state', 'in', ['draft', 'in_progress'])])
            })
        
        # 4. Risks / Blockers / High Priority
        blockers = self.env['analysis.daily.log'].search_count([('has_blockers', '=', True), ('date', '=', today)])
        waiting_requests = self.env['analysis.request'].search_count([('state', 'in', ['waiting_business', 'waiting_technical'])])
        escalated_actions = self.env['analysis.action.item'].search_count([('escalation_required', '=', True)])
        high_priority_requests = self.env['analysis.request'].search_count([('priority', 'in', ['high', 'urgent']), ('state', '!=', 'completed')])

        # 5. Delivery Snapshot
        req_summary = {
            'total': self.env['analysis.requirement'].search_count([]),
            'approved': self.env['analysis.requirement'].search_count([('state', '=', 'approved')]),
            'review': self.env['analysis.requirement'].search_count([('state', '=', 'in_review')]),
        }
        deliv_summary = {
            'draft': self.env['analysis.deliverable'].search_count([('state', '=', 'draft')]),
            'approved': approved_deliverables,
            'finalized': self.env['analysis.deliverable'].search_count([('state', '=', 'finalized')]),
        }

        # 6. Personal "My Work"
        my_work = {
            'requests': self.env['analysis.request'].search_count([('analyst_ids', 'in', user.id), ('state', 'not in', ['completed', 'closed', 'rejected'])]),
            'actions': self.env['analysis.action.item'].search_count([('owner_id', '=', user.id), ('state', '=', 'open')]),
            'deliverables': self.env['analysis.deliverable'].search_count([('analyst_ids', 'in', user.id), ('state', 'in', ['draft', 'in_progress'])]),
            'meetings': self.env['analysis.meeting'].search_count([
                ('meeting_datetime', '>=', today),
                ('meeting_datetime', '<', today + timedelta(days=1)),
                ('participant_ids', 'in', user.id)
            ]),
        }

        return {
            'kpis': {
                'open_requests': len(open_requests),
                'overdue_requests': len(overdue_requests),
                'pending_review_requests': pending_review_requests,
                'open_action_items': self.env['analysis.action.item'].search_count([('state', '=', 'open')]),
                'overdue_action_items': overdue_action_items,
                'approved_deliverables': approved_deliverables,
                'pending_review_deliverables': pending_review_deliverables,
                'meetings_today': meetings_today,
            },
            'pipeline': pipeline_data,
            'workload': workload_data,
            'risks': {
                'today_blockers': blockers,
                'waiting_requests': waiting_requests,
                'escalated_actions': escalated_actions,
                'high_priority_requests': high_priority_requests,
            },
            'snapshot': {
                'requirements': req_summary,
                'deliverables': deliv_summary,
            },
            'my_work': my_work,
        }
