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
        # Change Requests
        open_crs = self.env['analysis.change.request'].search([('state', 'not in', ['closed', 'rejected', 'converted'])])
        pending_impact_crs = self.env['analysis.change.request'].search_count([('state', 'in', ['under_review', 'pending_impact'])])
        pending_approval_crs = self.env['analysis.change.request'].search_count([('state', '=', 'pending_approval')])
        approved_crs = self.env['analysis.change.request'].search([('state', '=', 'approved')])
        total_cr_cost = sum(approved_crs.mapped('estimated_cost'))

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

        # 6. Personal "My Work" - Defined domains for both counting and frontend navigation
        my_req_domain = [('analyst_ids', 'in', user.id), ('state', 'not in', ['completed', 'closed', 'rejected'])]
        my_act_domain = [('owner_id', '=', user.id), ('state', '=', 'open')]
        my_del_domain = [('analyst_ids', 'in', user.id), ('state', 'in', ['draft', 'in_progress'])]
        my_mtg_domain = [
            ('participant_ids', 'in', user.id),
            ('meeting_datetime', '>=', today),
            ('meeting_datetime', '<', today + timedelta(days=1))
        ]

        my_work = {
            'requests': self.env['analysis.request'].search_count(my_req_domain),
            'actions': self.env['analysis.action.item'].search_count(my_act_domain),
            'deliverables': self.env['analysis.deliverable'].search_count(my_del_domain),
            'meetings': self.env['analysis.meeting'].search_count(my_mtg_domain),
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
            'change_requests': {
                'total_open': len(open_crs),
                'pending_impact': pending_impact_crs,
                'pending_approval': pending_approval_crs,
                'total_cost': total_cr_cost,
            },
            'domains': {
                'my_requests': my_req_domain,
                'my_actions': my_act_domain,
                'my_deliverables': my_del_domain,
                'my_meetings': my_mtg_domain,
            },
            'charts': {
                'type_distribution': self._get_type_distribution(),
                'monthly_velocity': self._get_monthly_velocity(),
            }
        }

    def _get_type_distribution(self):
        """Aggregate counts by Request Type for the Pie Chart"""
        query = """
            SELECT request_type, count(*) 
            FROM analysis_request 
            GROUP BY request_type
        """
        self.env.cr.execute(query)
        res = self.env.cr.fetchall()
        
        selection_map = dict(self.env['analysis.request']._fields['request_type'].selection)
        labels = []
        data = []
        for r_type, count in res:
            labels.append(selection_map.get(r_type, r_type))
            data.append(count)
        
        return {'labels': labels, 'data': data}

    def _get_monthly_velocity(self):
        """Aggregate counts by creation calendar month for the Velocity Chart"""
        labels = []
        data = []
        today = date.today()
        
        # Get start of current month
        current_iter = today.replace(day=1)
        
        # Collect last 6 months
        for i in range(6):
            month_label = current_iter.strftime('%b %Y')
            
            # Start and end of the specific calendar month
            start_month = current_iter
            if current_iter.month == 12:
                end_month = current_iter.replace(year=current_iter.year + 1, month=1)
            else:
                end_month = current_iter.replace(month=current_iter.month + 1)
                
            count = self.env['analysis.request'].search_count([
                ('create_date', '>=', fields.Datetime.to_string(start_month)),
                ('create_date', '<', fields.Datetime.to_string(end_month))
            ])
            
            # Insert at beginning to keep chronological order
            labels.insert(0, month_label)
            data.insert(0, count)
            
            # Move back 1 month
            if current_iter.month == 1:
                current_iter = current_iter.replace(year=current_iter.year - 1, month=12)
            else:
                current_iter = current_iter.replace(month=current_iter.month - 1)
            
        return {'labels': labels, 'data': data}
