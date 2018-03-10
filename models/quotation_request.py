# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models
from datetime import datetime
class QuotationRequest(models.Model):

    _name ="hr.expense_approval.request_quotation"
    _description = "Quotation Request"

    #_inherit = ['mail.thread', 'ir.needaction_mixin']

    name = fields.Char(string="Đề xuất")
    quotation_request_id = fields.Char(string="Mã",readonly=True)
    financial_activity = fields.Many2one('hr.expense_approval.financial_activity',string="Hoạt động Tài chính",store=True)
    cost_center_id = fields.Many2one('hr.expense_approval.financial_costcenter_approver',string="Mã dự toán",store=True)
    
    #Ngày đề nghị
    date = fields.Date(readonly=True, default=fields.Date.context_today, string="Ngày yêu cầu")
    payment_date = fields.Date(default=fields.Date.context_today, string="Ngày đề nghị thanh toán",required=True)
    
    #Người đề nghị
    employee_id = fields.Many2one('hr.employee', string="Người yêu cầu",readonly=True, required=True, default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1))
    company_id = fields.Many2one('res.company', string='Công ty', default=lambda self: self.env.user.company_id, store=True)
    #department_id = fields.Many2one('hr.department', string='Phòng ban', readonly=True, store=True)
    
    #Nguoi huong
    beneficiary = fields.Char(string="Người/Công ty thụ hưởng")

    #Số tiền
    currency_id = fields.Many2one('res.currency', string='Tiền tệ thanh toán', default=lambda self: self.env.user.company_id.currency_id)
    amount = fields.Float(string='Số tiền', required=True)
    currency_rate = fields.Float(string="Tỷ giá",required=True,default=1)
    amount_vnd = fields.Float(string='Số tiền (VND)', store=True, compute='_compute_amount_vnd')
    amount_text = fields.Char(string='Số tiền (VND) bằng chữ')

    attachment_number = fields.Integer(compute='_compute_attachment_number', string='Số chứng từ')
    pm_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp PM", readonly=True,store=True)
    td_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp TD",readonly=True,store=True)
    sd_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp SD",readonly=True,store=True)
    ce_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp CE",readonly=True,store=True)
    ceo_approver_id = fields.Many2one('hr.employee', string="Giám đốc",readonly=True,store=True)

    fi_ox_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp OX")
    # fi_pm_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp PM")
    # fi_td_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp TD")
    # fi_sd_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp SD")
    # fi_ce_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp CE")
    # fi_cfo_approver_id = fields.Many2one('hr.employee', string="Kế toán trưởng")


    #Status
    #sheet_id = fields.Many2one('hr.expense.approval.sheet', string="Expense Report", readonly=True, copy=False) 

    payment_request_id = fields.Char(string="Payment Request")
	# fields.Many2one('hr.expense_approval.request_payment',
    #                                    string='Các đề xuất dự toán',
    #                                    readonly=True,
    #                                     default=lambda self: self.env['hr.employee'].search([('quotation_request_id', '=', self.quotation_request_id)], limit=1))

    state = fields.Selection([
        ('draft', 'Bản draft'),
        ('confirmed', 'Chủ dự toán duyệt'),
        ('approved', 'Tài chính duyệt'),
        ('done', 'Hoàn thành')
        ],  string='Trạng thái', copy=False, index=True, readonly=True, store=True,
        help="Trạng thái của yêu cầu")

    @api.multi
    def action_draft(self):
        self.state = 'draft'

    @api.multi
    def action_confirm(self):
        self.state = 'confirmed'
        #send mail next approval
        #pm_approval_id
        #template mail: hr_

        #Trangnt_ send mail for approval
    
        #if self.env.context.get('send_email'):
        #
        #self.force_quotation_send()
     
        #if self.env['ir.values'].get_default('sale.config.settings', 'auto_done_setting'):
        #    self.action_done()
        
    @api.multi
    def action_quotation_send(self):
        # '''
        # This function opens a window to compose an email, with the edi sale template message loaded by default
        # '''
        #self.ensure_one()
        #ir_model_data = self.env['ir.model.data']
        #try:
        #    template_id = ir_model_data.get_object_reference('__export__', 'mail_template_16')[1]
        #except ValueError:
        #    template_id = False
        #try:
        #    compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        #except ValueError:
        #    compose_form_id = False
        #ctx = dict()
        #ctx.update({
        #    'default_model': 'hr.expense_approval.request_quotation',
        #    #'default_res_id': self.ids[0],
        #    'default_use_template': bool(template_id),
        #    'default_template_id': template_id,
        #    'default_composition_mode': 'comment',
        #    'mark_so_as_sent': True
        #    #,
        #    #'custom_layout': "sale.mail_template_data_notification_email_sale_order"
        #})
        #return {
        #    'type': 'ir.actions.act_window',
        #    'view_type': 'form',
        #    'view_mode': 'form',
        #    'res_model': 'mail.compose.message',
        #    'views': [(compose_form_id, 'form')],
        #    'view_id': compose_form_id,
        #    'target': 'new',
        #   'context': ctx,
        }

    
    @api.multi
    def force_quotation_send(self):
        # for quotation in self:
        #     email_act = quotation.action_quotation_send()
        #     if email_act and email_act.get('context'):
        #         email_ctx = email_act['context']
        #         email_ctx.update(default_email_from=order.company_id.email)
        #         order.with_context(email_ctx).message_post_with_template(email_ctx.get('default_template_id'))
        return True


    @api.multi
    def action_approve(self):
        self.state = 'approved'
        #approval PM,TD,SD,CE,CEO,
        
    @api.multi
    def action_done(self):
        self.state = 'done'
        #approval account
    
    @api.depends('amount', 'currency_id','currency_rate')
    def _compute_amount_vnd(self):
        for request_quotation in self:
            request_quotation.amount_vnd = request_quotation.amount * request_quotation.currency_rate
            
    
    @api.multi
    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].read_group([('res_model', '=', 'hr.expense_approval.request_quotation'), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for request_quotation in self:
            request_quotation.attachment_number = attachment.get(request_quotation.id, 0)
    
    @api.multi
    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'hr.expense_approval.request_quotation'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'hr.expense_approval.request_quotation', 'default_res_id': self.id}
        return res
    
    #@api.onchange('financial_activity')
    def _onchange_financial_activity(self):
        self.name = self.cost_center_id.name + " - " + self.financial_activity.name

    @api.onchange('cost_center_id')
    def _onchange_cost_center_id(self):
        self.pm_approver_id = self.cost_center_id.pm_approver_id
        self.td_approver_id = self.cost_center_id.td_approver_id
        self.sd_approver_id = self.cost_center_id.sd_approver_id
        self.ce_approver_id = self.cost_center_id.ce_approver_id
        self.ceo_approver_id = self.cost_center_id.ceo_approver_id
    
    @api.model
    def create(self,vals):
        vals["quotation_request_id"] = datetime.utcnow().strftime('%Y%m%d.%H%M%S%f')[:-3]
        #vals["name"]= selft.cost_center_id.name + "-" + self.financial_activity.name
        return super(QuotationRequest,self).create(vals)