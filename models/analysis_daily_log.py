from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AnalysisDailyLog(models.Model):
    """
    Daily Performance Tracking: Allows analysts to record their daily output.
    Aggregates planned vs actual work and captures blockers for management visibility.
    """
    _name = 'analysis.daily.log'
    _description = 'Analysis Daily Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Name', readonly=True, compute='_compute_name', store=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)
    analyst_id = fields.Many2one('res.users', string='Analyst', required=True, default=lambda self: self.env.user, tracking=True)
    
    planned_activities = fields.Html(string='Planned Activities')
    actual_activities = fields.Html(string='Actual Activities', required=True)
    meetings_summary = fields.Html(string='Meetings Summary')
    deliverables_produced = fields.Html(string='Deliverables Produced')
    blockers_risks = fields.Html(string='Blockers & Risks')
    pending_followups = fields.Html(string='Pending Follow-ups')
    next_day_plan = fields.Html(string='Next Day Plan')

    time_spent_hours = fields.Float(string='Time Spent (Hours)')
    reviewer_id = fields.Many2one('res.users', string='Reviewer', tracking=True)
    review_comment = fields.Html(string='Review Comment')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed')
    ], string='Status', required=True, default='draft', tracking=True)

    request_ids = fields.Many2many('analysis.request', relation='daily_log_req_rel', column1='log_id', column2='req_id', string='Analysis Requests')
    meeting_ids = fields.Many2many('analysis.meeting', relation='daily_log_meet_rel', column1='log_id', column2='meet_id', string='Meetings')
    deliverable_ids = fields.Many2many('analysis.deliverable', relation='daily_log_deliv_rel', column1='log_id', column2='deliv_id', string='Deliverables')

    request_count = fields.Integer(string='Requests Count', compute='_compute_request_count')
    meeting_count = fields.Integer(string='Meeting Count', compute='_compute_meeting_count')
    deliverable_count = fields.Integer(string='Deliverable Count', compute='_compute_deliverable_count')
    
    has_blockers = fields.Boolean(string='Has Blockers', compute='_compute_has_blockers', store=True)
    is_today = fields.Boolean(string='Is Today', compute='_compute_is_today', search='_search_is_today')
    is_late_submission = fields.Boolean(string='Late Submission', compute='_compute_is_late_submission', search='_search_is_late_submission')

    @api.depends('date', 'analyst_id.name')
    def _compute_name(self):
        for record in self:
            if record.date and record.analyst_id:
                record.name = f"Daily Log - {record.analyst_id.name} - {record.date}"
            else:
                record.name = _('New Daily Log')

    @api.depends('blockers_risks')
    def _compute_has_blockers(self):
        for record in self:
            if record.blockers_risks and record.blockers_risks.strip() not in ('<p><br></p>', '<p></p>', ''):
                record.has_blockers = True
            else:
                record.has_blockers = False

    def _compute_is_today(self):
        today = fields.Date.context_today(self)
        for record in self:
            record.is_today = (record.date == today)

    def _search_is_today(self, operator, value):
        today = fields.Date.context_today(self)
        is_today = value if operator in ('=', 'in') else not value
        if is_today:
            return [('date', '=', today)]
        return [('date', '!=', today)]

    def _compute_is_late_submission(self):
        today = fields.Date.context_today(self)
        for record in self:
            record.is_late_submission = (record.state == 'draft' and record.date and record.date < today)

    def _search_is_late_submission(self, operator, value):
        today = fields.Date.context_today(self)
        is_late = value if operator in ('=', 'in') else not value
        if is_late:
            return [('state', '=', 'draft'), ('date', '<', today)]
        return ['|', ('state', '!=', 'draft'), ('date', '>=', today)]

    @api.depends('request_ids')
    def _compute_request_count(self):
        for record in self:
            record.request_count = len(record.request_ids)

    @api.depends('meeting_ids')
    def _compute_meeting_count(self):
        for record in self:
            record.meeting_count = len(record.meeting_ids)

    @api.depends('deliverable_ids')
    def _compute_deliverable_count(self):
        for record in self:
            record.deliverable_count = len(record.deliverable_ids)

    def action_submit(self):
        for record in self:
            record.state = 'submitted'

    def action_mark_reviewed(self):
        for record in self:
            if not record.reviewer_id:
                record.reviewer_id = self.env.user.id
            record.state = 'reviewed'

    def action_reset_to_draft(self):
        for record in self:
            record.state = 'draft'
