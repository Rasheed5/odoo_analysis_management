from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AnalysisChangeRequest(models.Model):
    _name = 'analysis.change.request'
    _description = 'Change Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_received desc, id desc'

    # --- SECTION 1: General Project Information ---
    project_id = fields.Many2one('project.project', string='Project Name', tracking=True)
    project_code = fields.Char(string='Project Code', related='project_id.name', readonly=True) # Usually project doesn't have a code field by default unless added, using name for now
    current_phase_name = fields.Char(string='Current Phase Name')
    phase_number = fields.Char(string='Phase Number')
    customer_id = fields.Many2one('res.partner', string='Customer Name', tracking=True)
    system_version = fields.Char(string='System Version / Release')
    contract_date = fields.Date(string='Contract Signature Date')

    # --- SECTION 2: General Change Request Information ---
    name = fields.Char(string='Reference', required=True, readonly=True, default=lambda self: _('New'))
    title = fields.Char(string='Change Request Name', required=True, tracking=True)
    date_received = fields.Date(string='Date Received', default=fields.Date.context_today, tracking=True)
    receiver_id = fields.Many2one('res.users', string='Request Receiver Name', default=lambda self: self.env.user)
    request_reference = fields.Char(string='Request Reference')
    submitted_by = fields.Char(string='Request Submitted By (Client)')
    requester_role = fields.Char(string='Requester Title / Role')
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Emergency')
    ], string='Request Priority', default='medium', tracking=True)
    request_type = fields.Selection([
        ('major', 'Major'),
        ('minor', 'Minor'),
        ('emergency', 'Emergency'),
        ('other', 'Other')
    ], string='Request Type', default='minor', tracking=True)

    # --- SECTION 3: Change Request Description ---
    background = fields.Html(string='Background and Context')
    scope_reference = fields.Char(string='Scope Reference')
    detailed_description = fields.Html(string='Detailed Description of the Change Request', required=True)
    justification = fields.Html(string='Justification / Reasons')

    # --- SECTION 4: Change Impacts ---
    # A. Scope Impact
    phase_scope_impact = fields.Html(string='Phase Scope Impact')
    project_scope_impact = fields.Html(string='Project Scope Impact')
    impact_category = fields.Selection([
        ('gathering', 'Requirements Gathering and Analysis'),
        ('config', 'Configuration'),
        ('custom', 'Customization'),
        ('dev', 'Development'),
        ('integration', 'Integration'),
        ('reports', 'Reports / Forms'),
        ('perm', 'Permissions'),
        ('other', 'Other')
    ], string='Impact Category')

    # B. Affected Components
    component_ids = fields.One2many('analysis.change.request.component', 'change_request_id', string='Affected Components')

    # C. Schedule Impact
    schedule_impact_level = fields.Selection([
        ('none', 'No Impact'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], string='Schedule Impact Level', default='none')
    schedule_impact_notes = fields.Html(string='Schedule Impact Notes')

    # D. Resource Impact
    resource_impact_notes = fields.Html(string='Required Resources (preliminary)')

    # E. Cost Impact
    pricing_model = fields.Selection([
        ('fixed', 'Fixed Price'),
        ('tm', 'Time and Material'),
        ('other', 'Other')
    ], string='Pricing Model from Contract')
    
    estimated_work_days = fields.Float(string='Total Estimated Work Days', compute='_compute_total_days', store=True)
    days_analysis = fields.Float(string='Requirements & Analysis (Days)')
    days_config = fields.Float(string='Configuration / Setup (Days)')
    days_dev = fields.Float(string='Customization / Development (Days)')
    days_testing = fields.Float(string='Testing / Deployment (Days)')
    days_training = fields.Float(string='Training / Enablement (Days)')
    
    cost_calculation_mechanism = fields.Html(string='Cost Calculation Mechanism')
    estimated_cost = fields.Float(string='Estimated Cost', tracking=True)
    billing_mechanism = fields.Html(string='Billing Mechanism')

    # F. Outputs / Deliverables
    output_ids = fields.One2many('analysis.change.request.output', 'change_request_id', string='Expected Outputs')

    # G. Stakeholders
    stakeholder_ids = fields.One2many('analysis.change.request.stakeholder', 'change_request_id', string='Stakeholders Impact')

    # --- SECTION 5: Risks and Mitigation ---
    risk_ids = fields.One2many('analysis.change.request.risk', 'change_request_id', string='Risks and Mitigation')

    # --- SECTION 6: Alternatives and Recommendations ---
    proposed_alternatives = fields.Html(string='Proposed Alternative Solutions')
    final_recommendations = fields.Html(string='Final Company Recommendations')

    # --- SECTION 7: Assumptions and Constraints ---
    assumption_ids = fields.One2many('analysis.change.request.assumption', 'change_request_id', string='Assumptions')
    constraint_ids = fields.One2many('analysis.change.request.constraint', 'change_request_id', string='Constraints')

    # --- SECTION 8: Approval and Signature ---
    mutual_declarations = fields.Html(string='Mutual Declarations / Statements')
    client_decision = fields.Selection([
        ('accept', 'Accept'),
        ('postpone', 'Postpone'),
        ('reject', 'Reject')
    ], string='Client Final Decision', tracking=True)

    requester_sign_name = fields.Char(string='Requester Authorized Name')
    approver_sign_name = fields.Char(string='Approver Authorized Name')
    requester_sign_role = fields.Char(string='Requester Role')
    approver_sign_role = fields.Char(string='Approver Role')
    requester_sign_date = fields.Date(string='Requester Date')
    approver_sign_date = fields.Date(string='Approver Date')
    
    # Workflow State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('pending_impact', 'Pending Impact Analysis'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('postponed', 'Postponed'),
        ('rejected', 'Rejected'),
        ('converted', 'Converted to Analysis'),
        ('closed', 'Closed')
    ], string='Status', required=True, default='draft', tracking=True)

    analysis_request_id = fields.Many2one('analysis.request', string='Linked Analysis Request', readonly=True)

    @api.depends('days_analysis', 'days_config', 'days_dev', 'days_testing', 'days_training')
    def _compute_total_days(self):
        for record in self:
            record.estimated_work_days = sum([
                record.days_analysis, record.days_config, 
                record.days_dev, record.days_testing, 
                record.days_training
            ])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('analysis.change.request') or _('New')
        return super().create(vals_list)

    # --- Workflow actions ---
    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_review(self):
        self.write({'state': 'under_review'})

    def action_analyze_impact(self):
        self.write({'state': 'pending_impact'})

    def action_ready_for_approval(self):
        self.write({'state': 'pending_approval'})

    def action_approve(self):
        self.write({'state': 'approved', 'client_decision': 'accept'})

    def action_postpone(self):
        self.write({'state': 'postponed', 'client_decision': 'postpone'})

    def action_reject(self):
        self.write({'state': 'rejected', 'client_decision': 'reject'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    def action_convert_to_analysis(self):
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_("Only approved Change Requests can be converted to Analysis Requests."))
        
        if self.analysis_request_id:
            raise UserError(_("This Change Request has already been converted."))

        analysis_vals = {
            'title': self.title,
            'priority': self.priority,
            'description': self.detailed_description,
            'business_objective': self.justification,
            'project_id': self.project_id.id,
            'internal_note': _("Originating Change Request: %s") % self.name,
            'request_type': 'change_request', # Mapping to the existing type
        }
        
        # Pass expected outputs if any
        if self.output_ids:
            outputs = "\n".join(["- " + line.name for line in self.output_ids])
            analysis_vals['expected_output'] = outputs

        analysis_req = self.env['analysis.request'].create(analysis_vals)
        self.write({
            'analysis_request_id': analysis_req.id,
            'state': 'converted'
        })
        
        return {
            'name': _('Analysis Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'analysis.request',
            'res_id': analysis_req.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_analysis_request(self):
        self.ensure_one()
        return {
            'name': _('Analysis Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'analysis.request',
            'res_id': self.analysis_request_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

# --- Supporting Models ---

class AnalysisChangeRequestRisk(models.Model):
    _name = 'analysis.change.request.risk'
    _description = 'Change Request Risk'

    change_request_id = fields.Many2one('analysis.change.request', string='Change Request', ondelete='cascade')
    name = fields.Char(string='Risk', required=True)
    probability = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], string='Probability', default='medium')
    impact = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], string='Impact', default='medium')
    risk_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string='Risk Level', compute='_compute_risk_level', store=True)
    mitigation = fields.Text(string='Mitigation Action')
    owner_id = fields.Many2one('res.users', string='Owner / Responsible')

    @api.depends('probability', 'impact')
    def _compute_risk_level(self):
        for record in self:
            # Simple heuristic for risk level
            p = record.probability
            i = record.impact
            if p == 'high' and i == 'high':
                record.risk_level = 'critical'
            elif (p == 'high' or i == 'high') and (p != 'low' and i != 'low'):
                record.risk_level = 'high'
            elif p == 'low' and i == 'low':
                record.risk_level = 'low'
            else:
                record.risk_level = 'medium'

class AnalysisChangeRequestStakeholder(models.Model):
    _name = 'analysis.change.request.stakeholder'
    _description = 'Change Request Stakeholder'

    change_request_id = fields.Many2one('analysis.change.request', string='Change Request', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Stakeholder')
    name = fields.Char(string='Name/Department', help='Or Department Name')
    title = fields.Char(string='Title / Role')
    impact_degree = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], string='Impact Degree')
    impact_type = fields.Char(string='Impact Type')
    required_action = fields.Text(string='Required Action')

class AnalysisChangeRequestComponent(models.Model):
    _name = 'analysis.change.request.component'
    _description = 'Change Request Affected Component'

    change_request_id = fields.Many2one('analysis.change.request', string='Change Request', ondelete='cascade')
    name = fields.Char(string='Component Name', required=True)
    level = fields.Selection([
        ('system', 'System'),
        ('module', 'Module'),
        ('app', 'Application')
    ], string='Level', default='module')

class AnalysisChangeRequestOutput(models.Model):
    _name = 'analysis.change.request.output'
    _description = 'Change Request Output'
    change_request_id = fields.Many2one('analysis.change.request', string='Change Request', ondelete='cascade')
    name = fields.Char(string='Expected Output', required=True)

class AnalysisChangeRequestAssumption(models.Model):
    _name = 'analysis.change.request.assumption'
    _description = 'Change Request Assumption'
    change_request_id = fields.Many2one('analysis.change.request', string='Change Request', ondelete='cascade')
    name = fields.Char(string='Assumption', required=True)

class AnalysisChangeRequestConstraint(models.Model):
    _name = 'analysis.change.request.constraint'
    _description = 'Change Request Constraint'
    change_request_id = fields.Many2one('analysis.change.request', string='Change Request', ondelete='cascade')
    name = fields.Char(string='Constraint', required=True)
