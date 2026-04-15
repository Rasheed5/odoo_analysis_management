from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date

class AnalysisTag(models.Model):
    """
    Analysis Tag System:
    A centralized model to categorize all analysis records.
    Tags are shared across Requests, Requirements, Deliverables, etc.
    """
    _name = 'analysis.tag'
    _description = 'Analysis Tag'
    _order = 'name'

    name = fields.Char(string='Tag Name', required=True, translate=True)
    color = fields.Integer(string='Color Index', default=0)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Tag name must be unique!'),
    ]

class AnalysisRequest(models.Model):
    """
    Main model for the Analysis Management module.
    Represents a formal request for business or system analysis.
    Tracks the lifecycle from intake to completion.
    """
    _name = 'analysis.request'
    _description = 'Analysis Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Header section: Basic Identity
    name = fields.Char(string='Reference', required=True, readonly=True, default=lambda self: _('New'))
    title = fields.Char(string='Title', required=True, tracking=True)

    # Classification: Used for reporting and workload balancing
    request_type = fields.Selection([
        ('new_project', 'New Project'),
        ('new_system', 'New System'),
        ('new_feature', 'New Feature'),
        ('enhancement', 'Enhancement'),
        ('bug_analysis', 'Bug Analysis'),
        ('integration_analysis', 'Integration Analysis'),
        ('report_analysis', 'Report Analysis'),
        ('process_improvement', 'Process Improvement'),
        ('change_request', 'Change Request'),
        ('investigation', 'Investigation'),
        ('compliance_analysis', 'Compliance Analysis')
    ], string='Request Type', required=True, tracking=True)

    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string='Priority', required=True, default='medium', tracking=True)

    business_domain = fields.Char(string='Business Domain')
    related_system_module = fields.Char(string='Related System Module')
    tag_ids = fields.Many2many('analysis.tag', string='Tags')

    # Team Assignment
    requester_id = fields.Many2one('res.users', string='Requester', required=True, default=lambda self: self.env.user)
    analyst_ids = fields.Many2many('res.users', 'rel_request_analysts', 'request_id', 'user_id', string='Assigned Analysts', tracking=True)
    reviewer_id = fields.Many2one('res.users', string='Reviewer', tracking=True)
    manager_id = fields.Many2one('res.users', string='Manager')

    project_id = fields.Many2one('project.project', string='Project', tracking=True)

    # Lifecycle Dates
    date_requested = fields.Date(string='Date Requested', required=True, default=fields.Date.context_today)
    date_assigned = fields.Date(string='Date Assigned')
    due_date = fields.Date(string='Due Date', tracking=True)
    start_date = fields.Date(string='Start Date')
    completed_date = fields.Date(string='Completed Date')
    estimated_effort_hours = fields.Float(string='Estimated Effort (Hours)')
    actual_effort_hours = fields.Float(string='Actual Effort (Hours)')

    # Scope and Content: Qualitative breakdown of the analysis
    description = fields.Html(string='Description', required=True)
    business_objective = fields.Html(string='Business Objective')
    expected_output = fields.Html(string='Expected Output')
    scope_summary = fields.Html(string='Scope Summary')
    constraints = fields.Html(string='Constraints')
    assumptions = fields.Html(string='Assumptions')
    risks = fields.Html(string='Risks')
    internal_note = fields.Html(string='Internal Notes')

    # Workflow State Control
    state = fields.Selection([
        ('new', 'New'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('waiting_business', 'Waiting (Business)'),
        ('waiting_technical', 'Waiting (Technical)'),
        ('pending_review', 'Pending Final Review'),
        ('completed', 'Completed'),
        ('closed', 'Closed')
    ], string='Status', required=True, default='new', tracking=True)

    is_overdue = fields.Boolean(string='Overdue', compute='_compute_is_overdue', search='_search_is_overdue')
    days_open = fields.Integer(string='Days Open', compute='_compute_days_open')

    meeting_count = fields.Integer(string='Meetings', compute='_compute_meeting_count')
    requirement_count = fields.Integer(string='Requirements', compute='_compute_requirement_count')
    deliverable_count = fields.Integer(string='Deliverables', compute='_compute_deliverable_count')
    action_item_count = fields.Integer(string='Action Items', compute='_compute_action_item_count')

    # Linked Records
    meeting_ids = fields.One2many('analysis.meeting', 'request_id', string='Meetings')
    requirement_ids = fields.One2many('analysis.requirement', 'request_id', string='Requirements')
    deliverable_ids = fields.One2many('analysis.deliverable', 'request_id', string='Deliverables')
    action_item_ids = fields.One2many('analysis.action.item', 'request_id', string='Action Items')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('analysis.request') or _('New')
        return super().create(vals_list)

    @api.depends('due_date', 'state')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.due_date and record.state not in ['closed', 'completed', 'rejected']:
                record.is_overdue = record.due_date < today
            else:
                record.is_overdue = False

    def _search_is_overdue(self, operator, value):
        today = fields.Date.context_today(self)
        # Standardize the search value based on operator
        is_overdue = value if operator == '=' else not value
        
        if is_overdue:
            return [('due_date', '<', today), ('state', 'not in', ['closed', 'completed', 'rejected'])]
        else:
            return ['|', ('due_date', '>=', today), ('state', 'in', ['closed', 'completed', 'rejected'])]

    @api.depends('date_requested')
    def _compute_days_open(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.date_requested:
                delta = today - record.date_requested
                record.days_open = max(0, delta.days)
            else:
                record.days_open = 0

    @api.depends('meeting_ids')
    def _compute_meeting_count(self):
        for record in self:
            record.meeting_count = len(record.meeting_ids)

    @api.depends('requirement_ids')
    def _compute_requirement_count(self):
        for record in self:
            record.requirement_count = len(record.requirement_ids)

    @api.depends('deliverable_ids')
    def _compute_deliverable_count(self):
        for record in self:
            record.deliverable_count = len(record.deliverable_ids)

    @api.depends('action_item_ids')
    def _compute_action_item_count(self):
        for record in self:
            record.action_item_count = len(record.action_item_ids)

    def write(self, vals):
        # Trigger standard write first
        res = super(AnalysisRequest, self).write(vals)
        
        # Auto-set date assigned if analysts were added and date is missing
        if 'analyst_ids' in vals:
            for record in self:
                if record.analyst_ids and not record.date_assigned:
                    # Using super().write on individual record to avoid recursive write
                    super(AnalysisRequest, record).write({
                        'date_assigned': fields.Date.context_today(record)
                    })
        return res

    # --- Workflow actions ---
    def action_submit_for_review(self):
        for record in self:
            record.state = 'under_review'

    def action_approve(self):
        for record in self:
            record.state = 'approved'

    def action_reject(self):
        for record in self:
            record.state = 'rejected'

    def action_assign(self):
        for record in self:
            record.state = 'assigned'

    def action_start_work(self):
        for record in self:
            record.state = 'in_progress'
            if not record.start_date:
                record.start_date = fields.Date.context_today(record)

    def action_mark_waiting_business(self):
        for record in self:
            record.state = 'waiting_business'

    def action_mark_waiting_technical(self):
        for record in self:
            record.state = 'waiting_technical'

    def action_submit_for_final_review(self):
        for record in self:
            record.state = 'pending_review'

    def action_mark_completed(self):
        for record in self:
            record.state = 'completed'
            if not record.completed_date:
                record.completed_date = fields.Date.context_today(record)

    def action_close(self):
        for record in self:
            record.state = 'closed'

    def action_reset_to_new(self):
        for record in self:
            record.state = 'new'

    # --- Smart Button Actions ---
    def action_view_meetings(self):
        self.ensure_one()
        return {
            'name': _('Meetings'),
            'type': 'ir.actions.act_window',
            'res_model': 'analysis.meeting', # update once model is added
            'view_mode': 'list,form',
            'domain': [('request_id', '=', self.id)],
            'context': {'default_request_id': self.id},
        }

    def action_view_requirements(self):
        self.ensure_one()
        return {
            'name': _('Requirements'),
            'type': 'ir.actions.act_window',
            'res_model': 'analysis.requirement',
            'view_mode': 'list,form',
            'domain': [('request_id', '=', self.id)],
            'context': {'default_request_id': self.id},
        }

    def action_view_deliverables(self):
        self.ensure_one()
        return {
            'name': _('Deliverables'),
            'type': 'ir.actions.act_window',
            'res_model': 'analysis.deliverable',
            'view_mode': 'list,form',
            'domain': [('request_id', '=', self.id)],
            'context': {'default_request_id': self.id},
        }

    def action_view_action_items(self):
        self.ensure_one()
        return {
            'name': _('Action Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'analysis.action.item',
            'view_mode': 'list,form',
            'domain': [('request_id', '=', self.id)],
            'context': {'default_request_id': self.id},
        }
