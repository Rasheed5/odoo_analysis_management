from odoo import models, fields, api, _

class AnalysisRequirement(models.Model):
    """
    Requirement Management: The core asset of the analysis team.
    Captures individual business/software needs and tracks their approval state.
    """
    _name = 'analysis.requirement'
    _description = 'Analysis Requirement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, id desc'

    name = fields.Char(string='Requirement Ref', readonly=True, copy=False, default=lambda self: _('New'))
    title = fields.Char(string='Requirement Title', required=True, tracking=True)

    # Linked Resources
    request_id = fields.Many2one('analysis.request', string='Analysis Request', ondelete='cascade', tracking=True)
    project_id = fields.Many2one('project.project', string='Project', ondelete='set null')
    owner_id = fields.Many2one('res.users', string='Owner', required=True, default=lambda self: self.env.user, tracking=True)
    reviewer_id = fields.Many2one('res.users', string='Reviewer', tracking=True)
    analyst_ids = fields.Many2many('res.users', 'rel_requirement_analysts', 'req_id', 'user_id', string='Assigned Analysts', tracking=True)
    tag_ids = fields.Many2many('analysis.tag', string='Tags')

    # Requirement Classification
    priority = fields.Selection([
        ('low', 'Must be'),
        ('medium', 'Should be'),
        ('high', 'Could be'),
        ('critical', 'Won\'t have (this time)')
    ], string='MoSCoW Priority', default='medium', required=True, tracking=True)

    type = fields.Selection([
        ('business', 'Business Requirement'),
        ('user', 'User Story/Functional'),
        ('non_functional', 'Non-Functional/Technical'),
        ('logic', 'Business Logic/Calculation'),
        ('ui_ux', 'UI/UX/Wireframe Detail'),
        ('data', 'Data/Reporting Requirement')
    ], string='Requirement Type', required=True, default='business', tracking=True)

    complexity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], string='Complexity')

    description = fields.Html(string='Description', required=True)
    source = fields.Html(string='Source')
    dependencies = fields.Html(string='Dependencies')
    assumptions = fields.Html(string='Assumptions')
    constraints = fields.Html(string='Constraints')
    acceptance_criteria = fields.Html(string='Acceptance Criteria')
    business_rules = fields.Html(string='Business Rules')
    notes = fields.Html(string='Notes')

    version = fields.Char(string='Version', default='1.0', tracking=True)
    approval_comment = fields.Html(string='Approval Comment')
    approved_date = fields.Date(string='Approved Date', readonly=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_review', 'In Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('obsolete', 'Obsolete')
    ], string='Status', required=True, default='draft', tracking=True)

    # Hierarchy and Tracking
    parent_id = fields.Many2one('analysis.requirement', string='Parent Requirement', ondelete='set null')
    child_ids = fields.One2many('analysis.requirement', 'parent_id', string='Child Requirements')

    meeting_ids = fields.Many2many('analysis.meeting', relation='rel_requirement_meeting', column1='req_id', column2='meeting_id', string='Meetings')
    action_item_ids = fields.Many2many('analysis.action.item', relation='rel_action_item_requirement', column1='req_id', column2='item_id', string='Action Items')
    deliverable_ids = fields.Many2many('analysis.deliverable', relation='rel_deliverable_requirement', column1='req_id', column2='deliv_id', string='Linked Deliverables')

    meeting_count = fields.Integer(string='Meeting Count', compute='_compute_linked_counts')
    deliverable_count = fields.Integer(string='Deliverable Count', compute='_compute_linked_counts')
    action_item_count = fields.Integer(string='Action Item Count', compute='_compute_linked_counts')

    is_approved = fields.Boolean(string='Is Approved', compute='_compute_is_approved', store=True)
    has_acceptance_criteria = fields.Boolean(string='Has Acceptance Criteria', compute='_compute_text_flags', store=True)
    has_dependencies = fields.Boolean(string='Has Dependencies', compute='_compute_text_flags', store=True)

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
                vals['name'] = self.env['ir.sequence'].next_by_code('analysis.requirement') or _('New')
        return super().create(vals_list)

    @api.depends('meeting_ids', 'deliverable_ids', 'action_item_ids')
    def _compute_linked_counts(self):
        for record in self:
            record.meeting_count = len(record.meeting_ids)
            record.deliverable_count = len(record.deliverable_ids)
            record.action_item_count = len(record.action_item_ids)

    @api.depends('state')
    def _compute_is_approved(self):
        for record in self:
            record.is_approved = (record.state == 'approved')

    @api.depends('acceptance_criteria', 'dependencies')
    def _compute_text_flags(self):
        for record in self:
            record.has_acceptance_criteria = bool(record.acceptance_criteria and record.acceptance_criteria.strip() not in ('<p><br></p>', '<p></p>', ''))
            record.has_dependencies = bool(record.dependencies and record.dependencies.strip() not in ('<p><br></p>', '<p></p>', ''))

    def action_submit_review(self):
        for record in self:
            if record.state == 'draft':
                record.state = 'in_review'

    def action_approve(self):
        for record in self:
            if record.state in ['in_review', 'obsolete']: # Allow re-approval
                record.state = 'approved'
                record.approved_date = fields.Date.context_today(record)

    def action_reject(self):
        for record in self:
            if record.state == 'in_review':
                record.state = 'rejected'

    def action_mark_obsolete(self):
        for record in self:
            if record.state in ['draft', 'approved']:
                record.state = 'obsolete'

    def action_reset_to_draft(self):
        for record in self:
            record.state = 'draft'

    def action_view_action_items(self):
        self.ensure_one()
        return {
            'name': _('Action Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'analysis.action.item',
            'view_mode': 'kanban,list,form',
            'domain': [('requirement_ids', 'in', self.id)],
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

    def action_view_deliverables(self):
        self.ensure_one()
        return {
            'name': _('Deliverables'),
            'type': 'ir.actions.act_window',
            'res_model': 'analysis.deliverable',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.deliverable_ids.ids)],
            'context': {'default_request_id': self.request_id.id, 'default_requirement_ids': [(6, 0, [self.id])]},
        }
