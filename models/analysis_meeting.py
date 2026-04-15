from odoo import models, fields, api, _

class AnalysisMeeting(models.Model):
    """
    Meeting Management: Captures formal record of analysis workshops.
    Links participants, decisions, and outcomes to Analysis Requests.
    """
    _name = 'analysis.meeting'
    _description = 'Analysis Meeting'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'meeting_datetime desc, id desc'

    name = fields.Char(string='Meeting Subject', required=True, tracking=True)
    meeting_code = fields.Char(string='Meeting Code', readonly=True, copy=False, default=lambda self: _('New'))
    
    meeting_datetime = fields.Datetime(string='Date & Time', required=True, default=fields.Datetime.now, tracking=True)
    duration_hours = fields.Float(string='Duration (Hours)')
    organizer_id = fields.Many2one('res.users', string='Organizer', required=True, default=lambda self: self.env.user, tracking=True)

    participant_ids = fields.Many2many('res.users', string='Participants')
    external_participants_note = fields.Text(string='External Participants Note')
    
    request_id = fields.Many2one('analysis.request', string='Analysis Request', tracking=True)
    project_id = fields.Many2one('project.project', string='Project')
    tag_ids = fields.Many2many('analysis.tag', string='Tags')

    meeting_type = fields.Selection([
        ('requirement_gathering', 'Requirement Gathering'),
        ('workshop', 'Workshop'),
        ('review_meeting', 'Review Meeting'),
    ], string='Meeting Type', required=True, default='workshop', tracking=True)

    agenda = fields.Html(string='Agenda')
    discussion_notes = fields.Html(string='Discussion Notes')
    decisions = fields.Html(string='Decisions')
    open_questions = fields.Html(string='Open Questions')
    next_steps = fields.Html(string='Next Steps')

    state = fields.Selection([
        ('planned', 'Planned'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', required=True, default='planned', tracking=True)

    # Linked Resources: Many2manys allow meetings to cover multiple topics at once
    action_item_ids = fields.Many2many('analysis.action.item', relation='rel_action_item_meeting', column1='meeting_id', column2='item_id', string='Action Items')
    requirement_ids = fields.Many2many('analysis.requirement', relation='rel_requirement_meeting', column1='meeting_id', column2='req_id', string='Requirements')
    deliverable_ids = fields.Many2many('analysis.deliverable', relation='rel_deliverable_meeting', column1='meeting_id', column2='deliv_id', string='Deliverables')

    action_item_count = fields.Integer(string='Action Items Count', compute='_compute_linked_records_counts')
    requirement_count = fields.Integer(string='Requirements Count', compute='_compute_linked_records_counts')
    deliverable_count = fields.Integer(string='Deliverables Count', compute='_compute_linked_records_counts')
    participant_count = fields.Integer(string='Participant Count', compute='_compute_participant_count')

    is_past_meeting = fields.Boolean(string='Is Past Meeting', compute='_compute_is_past_meeting', search='_search_is_past_meeting')
    has_open_questions = fields.Boolean(string='Has Open Questions', compute='_compute_has_open_questions', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('meeting_code', _('New')) == _('New'):
                vals['meeting_code'] = self.env['ir.sequence'].next_by_code('analysis.meeting') or _('New')
        return super().create(vals_list)

    @api.depends('participant_ids')
    def _compute_participant_count(self):
        for record in self:
            record.participant_count = len(record.participant_ids)

    @api.depends('action_item_ids', 'requirement_ids', 'deliverable_ids')
    def _compute_linked_records_counts(self):
        for record in self:
            record.action_item_count = len(record.action_item_ids)
            record.requirement_count = len(record.requirement_ids)
            record.deliverable_count = len(record.deliverable_ids)

    @api.depends('meeting_datetime')
    def _compute_is_past_meeting(self):
        now = fields.Datetime.now()
        for record in self:
            record.is_past_meeting = bool(record.meeting_datetime and record.meeting_datetime < now)

    def _search_is_past_meeting(self, operator, value):
        now = fields.Datetime.now()
        is_past = value if operator in ('=', 'in') else not value
        if is_past:
            return [('meeting_datetime', '<', now)]
        return [('meeting_datetime', '>=', now)]

    @api.depends('open_questions')
    def _compute_has_open_questions(self):
        for record in self:
            record.has_open_questions = bool(record.open_questions and record.open_questions.strip() not in ('<p><br></p>', '<p></p>', ''))

    def action_mark_completed(self):
        for record in self:
            record.state = 'completed'

    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'

    def action_reset_to_planned(self):
        for record in self:
            record.state = 'planned'

    def action_view_action_items(self):
        self.ensure_one()
        return {
            'name': _('Action Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'analysis.action.item',
            'view_mode': 'list,form',
            'domain': [('meeting_ids', 'in', self.id)],
            'context': {},
        }

    def action_view_requirements(self):
        self.ensure_one()
        return {
            'name': _('Requirements'),
            'type': 'ir.actions.act_window',
            'res_model': 'analysis.requirement',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.requirement_ids.ids)],
        }

    def action_view_deliverables(self):
        self.ensure_one()
        return {
            'name': _('Deliverables'),
            'type': 'ir.actions.act_window',
            'res_model': 'analysis.deliverable',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.deliverable_ids.ids)],
        }
