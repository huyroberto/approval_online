# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models
from datetime import datetime

class PaymentRequest(models.Model):
    _name = "hr.expense_approval.request_payment"
    #_inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Yeu cau thanh toan"

    name = fields.Char(string="Yêu cầu thanh toán")
    payment_request_id = fields.Char(string="Mã",readonly=True)
    description = fields.Text(string="Nội dung")

     #Ngày đề nghị
    date = fields.Date(readonly=True, default=fields.Date.context_today, string="Ngày yêu cầu")
    
    #Người đề nghị
    employee_id = fields.Many2one('hr.employee', string="Người yêu cầu", required=True, default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1))
    company_id = fields.Many2one('res.company', string='Công ty', readonly=True, default=lambda self: self.env.user.company_id)
    #department_id = fields.Many2one('hr.department', string='Phòng ban', readonly=True)

    #Amount
    total_amount = fields.Float(string='Tổng tiền')#, compute='_compute_totalAmount')
    cash_amount = fields.Float(string='Tiền mặt')
    bank_amount = fields.Float(string='Ngân hàng')
    total_amount_text = fields.Char(string="Tổng tiền bằng chữ")

    total_cash_amount = fields.Float(string='Tổng tiền mặt', compute='_compute_totalAmount')
    total_bank_amount = fields.Float(string='Tổng tiền ngân hàng', compute='_compute_totalAmount')


    attachment_number = fields.Integer(compute='_compute_attachment_number', string='Số chứng từ')
    pm_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp PM")
    td_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp TD")
    sd_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp SD")
    ce_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp CE")
    ceo_approver_id = fields.Many2one('hr.employee', string="Giám đốc")

    fi_ox_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp OX")
    fi_pm_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp PM")
    fi_td_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp TD")
    fi_sd_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp SD")
    fi_ce_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp CE")
    fi_cfo_approver_id = fields.Many2one('hr.employee', string="Kế toán trưởng")

    #quotation request
    quotation_id = fields.Many2one('hr.expense_approval.request_quotation',
                                          string='Các đề xuất dự toán',required=True)

    total_amount_quotations = fields.Float(string='Tong tien du toan',
                                           compute='_compute_total_amount')
    #Line
    expense_line_ids = fields.One2many('hr.expense_approval.request_payment.line', 'payment_id', string="Các lịch thanh toán",ondelete="cascade", copy=False)
    #Status
    #sheet_id = fields.Many2one('hr.expense.approval.sheet', string="Expense Report", readonly=True, copy=False)
    state = fields.Selection([
        ('draft', 'Submit To Manager'),
        ('confirmed', 'Chủ dự toán duyệt'),
        ('approved', 'Tài chính duyệt'),
        ('done', 'Hoàn thành')
        ],  string='Trạng thái', copy=False, index=True, readonly=True, store=True,
        help="Status of the request.")

    @api.multi
    def action_draft(self):
        self.state = 'draft'

    @api.multi
    def action_confirm(self):
        self.state = 'confirmed'

    @api.multi
    def action_approve(self):
        self.state = 'approved'

    @api.multi
    def action_done(self):
        self.state = 'done'

    #@api.depends('quotation_line_ids')
    @api.onchange('quotation_line_ids')
    #@api.multi
    def _compute_total_amount(self):
        #self.total_amount = 100
        total = 0
        # if(self.quotation_line_ids)
        #     for quotation_line in self.quotation_line_ids:
        #         total= total+ quotation_line.amount_vnd
        # self.total_amount = total
        # self.total_amount_quotations = total

    #s
    @api.onchange('expense_line_ids')
    #@api.multi
    def _compute_totalAmount(self):
        total_cash = 0.0
        total_bank = 0.0
        for expense in self.expense_line_ids:
            total_cash = total_cash + expense.cash_amount
            total_bank = total_bank + expense.bank_amount

        self.total_cash_amount = total_cash
        self.total_bank_amount = total_bank

    @api.multi
    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].read_group([('res_model', '=', 'hr.expense_approval.request_payment'), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for request_payment in self:
            request_payment.attachment_number = attachment.get(request_payment.id, 0)
    @api.multi
    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'hr.expense_approval.request_payment'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'hr.expense_approval.request_payment', 'default_res_id': self.id}
        return res
    @api.model
    def create(self,vals):
        vals["payment_request_id"] = datetime.utcnow().strftime('%Y%m%d.%H%M%S%f')[:-3]
        #vals["name"]= vals["cost_center_id"].name + "-" vals["financial_activity"].name
        return super(PaymentRequest,self).create(vals)

class PaymentRequestLine(models.Model):
    _name = "hr.expense_approval.request_payment.line"
    #_description = "Lịch thanh toán"
    payment_id = fields.Many2one('hr.expense_approval.request_payment', string="Yêu cầu thanh toán", readonly=True, copy=False)

    name = fields.Char(string="Nội dung")
    #Ngày đề nghị
    payment_date = fields.Date(default=fields.Date.context_today, string="Ngày đề nghị thanh toán")

    #Thông tin chuyển khoản
    bank_owner = fields.Char(string="Chủ tài khoản")
    bank_name = fields.Char(string="Ngân hàng")
    bank_branch = fields.Char(string="Chi nhánh")
    bank_city = fields.Char(string="Thành phố")
    bank_account = fields.Char(string="Số tài khoản")
    bank_content = fields.Char(string="Nội dung chuyển khoản")
    
    #Amount
    total_amount = fields.Float(string="Tổng tiền", compute='_compute_total_amount')
    cash_amount = fields.Float(string="Tiền mặt",)
    bank_amount = fields.Float(string="Ngân hàng")
    total_amount_text = fields.Char(string="Tổng tiền bằng chữ")

    state = fields.Selection([
        ('open', 'Chưa thanh toán'),
        ('paid', 'Đã thanh toán')
        ],  string='Trạng thái', copy=False, index=True)

    attachment_number = fields.Integer(compute='_compute_attachment_number', string='Số chứng từ')
    @api.multi
    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].read_group([('res_model', '=', 'hr.expense_approval.request_payment.line'), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for request_payment in self:
            request_payment.attachment_number = attachment.get(request_payment.id, 0)
    @api.multi
    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'hr.expense_approval.request_payment.line'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'hr.expense_approval.request_payment.line', 'default_res_id': self.id}
        return res

    @api.depends('cash_amount', 'bank_amount')
    def _compute_total_amount(self):
        self.total_amount = self.cash_amount + self.bank_amount
    
