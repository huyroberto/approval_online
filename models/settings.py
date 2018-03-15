# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models

class FinancialActivity(models.Model):
    _name = "hr.expense_approval.financial_activity"
    #_description = "Hoạt động tài chính"

    name = fields.Char(string="Tên hoạt động",required=True)
    description = fields.Text(string="Mô tả")
    attachment_number = fields.Integer(compute='_compute_attachment_number', string='Số chứng từ')
    
    payent_lines = fields.One2many('hr.expense_approval.financial_activity_payment', 'financial_activity', string="Bút toán hạch toán",ondelete="cascade", copy=False)
    attachments = fields.Many2many(
                      comodel_name="ir.attachment", relation="financial_activity_ir_attachment_relation",
		       column1="activity_id", column2="attachment_id", string="Biểu mẫu, quy trình",)
    status = fields.Selection([
        ('active', 'Có hiệu lực'),
        ('inactive', 'Không hiệu lực')
        ],  string='Trạng thái', copy=False, index=True, store=True,
        )
    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].read_group([('res_model', '=', 'hr.expense_approval.financial_activity'), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for request_quotation in self:
            request_quotation.attachment_number = attachment.get(request_quotation.id, 0)

    @api.multi
    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
        res['domain'] = [('res_model', '=', 'hr.expense_approval.financial_activity'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'hr.expense_approval.financial_activity', 'default_res_id': self.id}
        return res

class FinancialActivityPaymentLine(models.Model):
    _name = 'hr.expense_approval.financial_activity_payment'

    financial_activity = fields.Many2one('hr.expense_approval.financial_activity',string='Hoạt động')
    description = fields.Char(string='Nội dung thanh toán')
    debit_account = fields.Many2one('account.account', string='Tài khoản ghi nợ')
    credit_account = fields.Many2one('account.account', string='Tài khoản ghi có')
    payment_time = fields.Selection([
        ('in', 'Trong kỳ'),
        ('out', 'Ngoài kỳ')], default='in',string="Kỳ hạch toán",copy=False,store=True)
        

class FinancialCostCenterApprover(models.Model):
    _name = "hr.expense_approval.financial_costcenter_approver"
    name = fields.Char(string="Mã dự toán",required=True)

    
    pm_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp PM")
    td_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp TD")
    sd_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp SD")
    ce_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp CE")
    ceo_approver_id = fields.Many2one('hr.employee', string="Giám đốc")

class RequestLocation(models.Model):
    _name = "hr.expense_approval.location"
    name = fields.Char(string="Địa điểm")

class ApprovalLevel(models.Model):
    _name = "hr.expense_approval.level"
    name = fields.Char(string="Mức phê duyệt")
    from_amount = fields.Integer(string="Từ số tiền",default=0,required=True)
    to_amount = fields.Integer(string="Tới số tiền",required=True)
    level = fields.Selection([
        ('pm', 'PM'),
        ('td', 'TD'),
        ('sd', 'SD'),
        ('ce', 'CE')
        ],  string='Cấp phê duyệt', index=True, store=True)

class FinancialApprovalLevel(models.Model):
    _name = "hr.expense_approval.financial_level"
    name = fields.Char(string="Mức phê duyệt")
    from_amount = fields.Integer(string="Từ số tiền",default=0,required=True)
    to_amount = fields.Integer(string="Tới số tiền",required=True)
    level = fields.Selection([
        ('pm', 'PM'),
        ('td', 'TD'),
        ('sd', 'SD'),
        ('ce', 'CE')
        ],  string='Cấp phê duyệt', index=True, store=True)


class CompanyFinancialApproval(models.Model):
    _name = "hr.expense_approval.company_financial_approval"
    #_description = "Hoạt động tài chính"
    company_id = fields.Many2one('res.company', string='Công ty',required=True)
    
    ox_approver_id = fields.Many2one('hr.employee', string="Nhân viên phụ trách")
    pm_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp PM")
    td_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp TD")
    sd_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp SD")
    ce_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp CE")
    plan_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp Kế hoạch")

    status = fields.Selection([
        ('active', 'Có hiệu lực'),
        ('inactive', 'Không hiệu lực')
        ],  string='Trạng thái', copy=False, index=True, store=True,
        )