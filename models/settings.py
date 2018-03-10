# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models

class FinancialActivity(models.Model):
    _name = "hr.expense_approval.financial_activity"
    #_description = "Hoạt động tài chính"

    name = fields.Char(string="Tên hoạt động",required=True)
    description = fields.Text(string="Mô tả")
    debit_account = fields.Many2one('account.account', string='Tài khoản ghi nợ')
    credit_account = fields.Many2one('account.account', string='Tài khoản ghi có')
    attachment_number = fields.Integer(compute='_compute_attachment_number', string='Số chứng từ')

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

class FinancialCostCenterApprover(models.Model):
    _name = "hr.expense_approval.financial_costcenter_approver"
    name = fields.Char(string="Mã dự toán",required=True)
    pm_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp PM", store=True)
    td_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp TD")
    sd_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp SD")
    ce_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp CE")
    ceo_approver_id = fields.Many2one('hr.employee', string="Giám đốc")

class RequestLocation(models.Model):
    _name = "hr.expense_approval.location"
    name = fields.Char(string="Địa điểm")