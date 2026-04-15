from odoo import models, fields, api, _

class AnalysisActionItem(models.Model):
    """
    Action Item System: A decentralized task pool.
    Action items can be linked to multiple sources (Meetings, Requirements, Deliverables).
    This allows follow-up items to be tracked in a unified way.
    """
    _name = 'analysis.action.item'
    _description = 'Analysis Action Item'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, due_date asc, id desc'

    name = fields.Char(string='Title', required=True, tracking=True)
    reference = fields.Char(string='Reference', readonly=True, copy=False, default=lambda self: _('New'))

    owner_id = fields.Many2one('res.users', string='Owner', required=True, tracking=True)
    created_by = fields.Many2one('res.users', string='Created By', required=True, default=lambda self: self.env.user, readonly=True)
    reviewer_id = fields.Many2one('res.users', string='Reviewer')

    source_type = fields.Selection([
        ('meeting', 'Meeting'),
        ('request', 'Request'),
        ('deliverable_review', 'Deliverable Review'),
        ('requirement_review', 'Requirement Review'),
        ('daily_log', 'Daily Log'),
        ('other', 'Other')
    ], string='Source Type', required=True, default='other', tracking=True)

    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string='Priority', required=True, default='medium', tracking=True)

    due_date = fields.Date(string='Due Date', tracking=True)
    start_date = fields.Date(string='Start Date', default=fields.Date.context_today)
    completed_date = fields.Date(string='Completed Date', readonly=True)
    
    followup_notes = fields.Text(string='Follow-up Notes')
    resolution_note = fields.Text(string='Resolution Note')
    
    escalation_required = fields.Boolean(string='Escalation Required', tracking=True)
    escalation_note = fields.Text(string='Escalation Note')

    # source_type determines which link fields are visible in the UI
    source_type = fields.Selection([
        ('direct', 'Direct / Manual'),
        ('meeting', 'Meeting Task'),
        ('request', 'Request Action'),
        ('requirement_review', 'Requirement Review Item'),
        ('deliverable_review', 'Deliverable Review Item')
    ], string='Source Category', default='direct', required=True)

    # Many2many Architecture: Allows an item to be linked to multiple parent records simultaneously.
    # We use plural names (meeting_ids, etc.) to ensure Odoo creates correct join tables.
    meeting_ids = fields.Many2many('analysis.meeting', relation='rel_action_item_meeting', column1='item_id', column2='meeting_id', string='Meetings')
    request_id = fields.Many2one('analysis.request', string='Analysis Request', ondelete='set null')
    requirement_ids = fields.Many2many('analysis.requirement', relation='rel_action_item_requirement', column1='item_id', column2='req_id', string='Requirements')
    deliverable_ids = fields.Many2many('analysis.deliverable', relation='rel_action_item_deliverable', column1='item_id', column2='deliv_id', string='Deliverables')
    daily_log_id = fields.Many2one('analysis.daily.log', string='Daily Log', ondelete='set null')
    tag_ids = fields.Many2many('analysis.tag', string='Tags')

    # Time Metrics: Computed fields for aging and overdue tracking
    is_overdue = fields.Boolean(string='Overdue', compute='_compute_time_metrics', search='_search_is_overdue')
    days_to_due = fields.Integer(string='Days to Due', compute='_compute_time_metrics')
    days_open = fields.Integer(string='Days Open', compute='_compute_time_metrics')
    
    is_blocked = fields.Boolean(string='Is Blocked', compute='_compute_is_blocked', store=True)

    state = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('waiting', 'Waiting'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', required=True, default='open', tracking=True)

    source_display = fields.Char(string='Source', compute='_compute_source_display')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('New')) == _('New'):
                vals['reference'] = self.env['ir.sequence'].next_by_code('analysis.action.item') or _('New')
        return super().create(vals_list)

    @api.depends('due_date', 'start_date', 'create_date', 'state')
    def _compute_time_metrics(self):
        for record in self:
            today = fields.Date.context_today(record)
            # Days Open
            start = record.start_date or (record.create_date and record.create_date.date()) or today
            if record.state in ['done', 'cancelled'] and record.completed_date:
                record.days_open = (record.completed_date - start).days
            else:
                record.days_open = (today - start).days

            # Overdue and Days to due
            if record.due_date:
                record.days_to_due = (record.due_date - today).days
                record.is_overdue = record.days_to_due < 0 and record.state not in ['done', 'cancelled']
            else:
                record.days_to_due = 0
                record.is_overdue = False

    def _search_is_overdue(self, operator, value):
        today = fields.Date.context_today(self)
        if operator == '=' and value:
            return [('due_date', '<', today), ('state', 'not in', ['done', 'cancelled'])]
        if operator == '=' and not value:
            return ['|', ('due_date', '>=', today), ('state', 'in', ['done', 'cancelled'])]
        return []

    @api.depends('state')
    def _compute_is_blocked(self):
        for record in self:
            record.is_blocked = (record.state == 'waiting')

    @api.depends('source_type', 'meeting_ids', 'request_id', 'requirement_ids', 'deliverable_ids', 'daily_log_id')
    def _compute_source_display(self):
        for record in self:
            if record.source_type == 'meeting' and record.meeting_ids:
                record.source_display = f"Meeting: {record.meeting_ids[0].name}"
            elif record.source_type == 'request' and record.request_id:
                record.source_display = f"Request: {record.request_id.name}"
            elif record.source_type == 'requirement_review' and record.requirement_ids:
                record.source_display = f"Requirement: {record.requirement_ids[0].name}"
            elif record.source_type == 'deliverable_review' and record.deliverable_ids:
                record.source_display = f"Deliverable: {record.deliverable_ids[0].name}"
            elif record.source_type == 'daily_log' and record.daily_log_id:
                record.source_display = f"Daily Log: {record.daily_log_id.name}"
            else:
                record.source_display = "Other / Unknown Source"

    @api.onchange('meeting_ids')
    def _onchange_meeting_ids(self):
        if self.meeting_ids and self.meeting_ids[0].request_id:
            self.request_id = self.meeting_ids[0].request_id

    def action_start_progress(self):
        for record in self:
            if record.state == 'open':
                record.state = 'in_progress'

    def action_mark_waiting(self):
        for record in self:
            record.state = 'waiting'

    def action_mark_done(self):
        for record in self:
            record.state = 'done'
            record.completed_date = fields.Date.context_today(record)

    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'

    def action_reset_to_open(self):
        for record in self:
            record.state = 'open'
            record.completed_date = False
