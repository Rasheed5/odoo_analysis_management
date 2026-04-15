from odoo import models, fields, api, _

class AnalysisDeliverable(models.Model):
    """
    Deliverable Management: Tracks formal outputs of the analysis phase (BRDs, SRS, Maps).
    Ensures that documents are reviewed and approved before baseline.
    """
    _name = 'analysis.deliverable'
    _description = 'Analysis Deliverable'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'planned_due_date asc, id desc'

    name = fields.Char(string='Deliverable Ref', readonly=True, copy=False, default=lambda self: _('New'))
    title = fields.Char(string='Deliverable Title', required=True, tracking=True)

    # Classification and Tracing
    type = fields.Selection([
        ('brd', 'Business Requirement Document (BRD)'),
        ('srs', 'Software Requirements Spec (SRS)'),
        ('process_map', 'Process Map/Flowchart'),
        ('wireframe', 'Wireframes/Mockups'),
        ('data_dict', 'Data Dictionary'),
        ('uat_plan', 'UAT Plan/Scenario'),
        ('gap_analysis', 'Gap Analysis/Assessment'),
        ('other', 'Other Supporting Document')
    ], string='Deliverable Type', required=True, default='brd', tracking=True)

    request_id = fields.Many2one('analysis.request', string='Analysis Request', ondelete='set null', tracking=True)
    project_id = fields.Many2one('project.project', string='Project', ondelete='set null')
    analyst_ids = fields.Many2many('res.users', 'rel_deliverable_analysts', 'deliv_id', 'user_id', string='Analysts/Authors', tracking=True)
    reviewer_id = fields.Many2one('res.users', string='Reviewer', tracking=True)
    tag_ids = fields.Many2many('analysis.tag', string='Tags')

    # Document Management
    external_link = fields.Char(string='Document Link', help='SharePoint, Confluence or Drive link')
    version = fields.Char(string='Version', default='1.0', tracking=True)
    planned_due_date = fields.Date(string='Planned Due Date', tracking=True)
    submission_date = fields.Date(string='Submission Date', readonly=True, tracking=True)
    approval_date = fields.Date(string='Approval Date', readonly=True, tracking=True)

    summary = fields.Html(string='Summary')
    review_comments = fields.Html(string='Review Comments')
    final_note = fields.Html(string='Final Note')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('pending_review', 'Pending Review'),
        ('review_feedback', 'Review Feedback'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('finalized', 'Finalized')
    ], string='Status', required=True, default='draft', tracking=True)
 
    # Linked Resources
    action_item_ids = fields.Many2many('analysis.action.item', relation='rel_action_item_deliverable', column1='deliv_id', column2='item_id', string='Action Items')
    meeting_ids = fields.Many2many('analysis.meeting', relation='rel_deliverable_meeting', column1='deliv_id', column2='meeting_id', string='Meetings')
    requirement_ids = fields.Many2many('analysis.requirement', relation='rel_deliverable_requirement', column1='deliv_id', column2='req_id', string='Linked Requirements')

    requirement_count = fields.Integer(string='Requirements Count', compute='_compute_linked_counts')
    action_item_count = fields.Integer(string='Action Items Count', compute='_compute_linked_counts')
    meeting_count = fields.Integer(string='Meetings Count', compute='_compute_linked_counts')

    review_cycle_count = fields.Integer(string='Review Cycles', default=0, copy=False)

    is_overdue = fields.Boolean(string='Overdue', compute='_compute_is_overdue', search='_search_is_overdue')
    is_approved = fields.Boolean(string='Is Approved', compute='_compute_state_flags', store=True)
    is_finalized = fields.Boolean(string='Is Finalized', compute='_compute_state_flags', store=True)

    @api.onchange('request_id')
    def _onchange_request_id(self):
        """Auto-populate project and analysts from the linked request"""
        if self.request_id:
            self.project_id = self.request_id.project_id
            self.analyst_ids = [(6, 0, self.request_id.analyst_ids.ids)]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('analysis.deliverable') or _('New')
        return super().create(vals_list)

    @api.depends('requirement_ids', 'action_item_ids', 'meeting_ids')
    def _compute_linked_counts(self):
        for record in self:
            record.requirement_count = len(record.requirement_ids)
            record.action_item_count = len(record.action_item_ids)
            record.meeting_count = len(record.meeting_ids)

    @api.depends('planned_due_date', 'state')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.planned_due_date and record.state not in ['approved', 'finalized', 'rejected']:
                record.is_overdue = record.planned_due_date < today
            else:
                record.is_overdue = False

    def _search_is_overdue(self, operator, value):
        today = fields.Date.context_today(self)
        if operator == '=' and value:
            return [('planned_due_date', '<', today), ('state', 'not in', ['approved', 'finalized', 'rejected'])]
        if operator == '=' and not value:
            return ['|', ('planned_due_date', '>=', today), ('state', 'in', ['approved', 'finalized', 'rejected'])]
        return []

    @api.depends('state')
    def _compute_state_flags(self):
        for record in self:
            record.is_approved = (record.state == 'approved')
            record.is_finalized = (record.state == 'finalized')

    def action_start_drafting(self):
        for record in self:
            if record.state == 'draft':
                record.state = 'in_progress'

    def action_submit_review(self):
        for record in self:
            if record.state in ['in_progress', 'review_feedback']:
                if not record.submission_date:
                    record.submission_date = fields.Date.context_today(record)
                record.state = 'pending_review'

    def action_send_back(self):
        for record in self:
            if record.state == 'pending_review':
                record.state = 'review_feedback'
                record.review_cycle_count += 1

    def action_approve(self):
        for record in self:
            if record.state == 'pending_review':
                record.state = 'approved'
                record.approval_date = fields.Date.context_today(record)

    def action_reject(self):
        for record in self:
            if record.state == 'pending_review':
                record.state = 'rejected'

    def action_finalize(self):
        for record in self:
            if record.state == 'approved':
                record.state = 'finalized'

    def action_reset_to_draft(self):
        for record in self:
            record.state = 'draft'

    def action_view_requirements(self):
        self.ensure_one()
        return {
            'name': _('Requirements'),
            'type': 'ir.actions.act_window',
            'res_model': 'analysis.requirement',
            'view_mode': 'kanban,list,form',
            'domain': [('id', 'in', self.requirement_ids.ids)],
            'context': {'default_request_id': self.request_id.id, 'default_deliverable_ids': [(6, 0, [self.id])]},
        }

    def action_view_action_items(self):
        self.ensure_one()
        return {
            'name': _('Action Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'analysis.action.item',
            'view_mode': 'kanban,list,form',
            'domain': [('deliverable_ids', 'in', self.id)],
            'context': {},
        }

    def action_view_meetings(self):
        self.ensure_one()
        return {
            'name': _('Meetings'),
            'type': 'ir.actions.act_window',
            'res_model': 'analysis.meeting',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.meeting_ids.ids)],
        }
