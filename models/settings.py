# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models

class FinancialActivity(models.Model):
    _name = "hr.expense_approval.financial_activity"
    _description = u'Thông tin hoạt động tài chính'
    #_description = "Hoạt động tài chính"
    name = fields.Char(string="Tên hoạt động",required=True)
    description = fields.Text(string="Mô tả")
    
    
    payment_lines = fields.One2many('hr.expense_approval.financial_activity_payment', 'financial_activity', string="Bút toán hạch toán",ondelete="cascade", copy=False)
    documents = fields.One2many(
            'hr.expense_approval.financial_activity_document',
            'financial_activity',
            string = 'Tài liệu, chứng từ',
            ondelete='cascade',
            copy=False
        )
    status = fields.Selection([
        ('active', 'Có hiệu lực'),
        ('inactive', 'Không hiệu lực')
        ],  string='Trạng thái', copy=False, index=True, store=True,
        )
    
class FinancialActivityPaymentLine(models.Model):
    _name = 'hr.expense_approval.financial_activity_payment'
    _description = u'Bút toán hoạch toán tài khoản của các hoạt động tài chính'
    name = fields.Char(string='Bút toán')
    financial_activity = fields.Many2one('hr.expense_approval.financial_activity',string='Hoạt động')
    
    debit_account = fields.Many2one('account.account', string='Tài khoản ghi nợ')
    credit_account = fields.Many2one('account.account', string='Tài khoản ghi có')
    payment_time = fields.Selection([
        ('in', 'Trong kỳ'),
        ('out', 'Ngoài kỳ')], default='in',string="Kỳ hạch toán",copy=False,store=True)
        
class FinancialActivityDocument(models.Model):
    _name = 'hr.expense_approval.financial_activity_document'
    name = fields.Char(string = 'Tên tài liệu, chứng từ',required=True)
    financial_activity = fields.Many2one('hr.expense_approval.financial_activity',string='Hoạt động')
    link = fields.Char(string = 'Link')
    required = fields.Selection([
        ('required', 'Bắt buộc'),
        ('not_required', 'Không bắt buộc')
    ],string='Bắt buộc trong hồ sơ',index=True,store=True)
    

#MÃ DỰ TOÁN
class CostCenter(models.Model):
    _name = "hr.expense_approval.cost_center"
    name = fields.Char(string="Mã chủ dự toán",required=True)
    
    td = fields.Many2one('res.users', string="TD")
    sd = fields.Many2one('res.users', string="SD")
    ce = fields.Many2one('res.users', string="CE")
    ceo = fields.Many2one('res.users', string="Giám đốc")

    codes = fields.One2many('hr.expense_approval.cost_center_code','cost_center',string='Các mã dự toán')

class CostCenterCode(models.Model):
    _name = 'hr.expense_approval.cost_center_code'
    name = fields.Char(string = "Mã", required=True)
    description = fields.Char(string="Nội dung", required=True)
    cost_center = fields.Many2one('hr.expense_approval.cost_center', string='Mã chủ dự toán')



class Location(models.Model):
    _name = "hr.expense_approval.location"
    name = fields.Char(string="Địa điểm")

class CostCenterApprovalLevel(models.Model):
    _name = "hr.expense_approval.cost_center_level"
    name = fields.Char(string="Mức phê duyệt")
    from_amount = fields.Integer(string="Từ số tiền",default=0,required=True)
    to_amount = fields.Integer(string="Tới số tiền",required=True)
    level = fields.Selection([
        ('pm', 'PM phê duyệt'),
        ('td', 'TD phê duyệt'),
        ('sd', 'SD phê duyệt'),
        ('ce', 'CE phê duyệt')
        ], default='pm',  string='Cấp phê duyệt', index=True, store=True)

    @api.model
    def create(self,vals):
        vals["name"] = vals["level"].upper()
        return super(CostCenterApprovalLevel,self).create(vals)

class CompanyInfo(models.Model):
    _name = "hr.expense_approval.company"
    #_description = "Hoạt động tài chính"
    company = fields.Many2one('res.company', string='Công ty',required=True)
    
    ox = fields.Many2one('res.users', string="Nhân viên phụ trách")
    pm = fields.Many2one('res.users', string="Phê duyệt cấp PM")
    td = fields.Many2one('res.users', string="Phê duyệt cấp TD")
    sd = fields.Many2one('res.users', string="Phê duyệt cấp SD")
    ce = fields.Many2one('res.users', string="Phê duyệt cấp CE")
    plan = fields.Many2one('res.users', string="Phê duyệt cấp Kế hoạch")

    approval_levels = fields.One2many('hr.expense_approval.company_level','company',string='Mức phê duyệt', required=True)

class CompanyApprovalLevel(models.Model):
    _name = "hr.expense_approval.company_level"
    name = fields.Char(string='Mức phê duyệt')
    company = fields.Many2one('hr.expense_approval.company',string='Công ty')
    from_amount = fields.Integer(string="Từ số tiền",default=0,required=True)
    to_amount = fields.Integer(string="Tới số tiền",required=True)
    level = fields.Selection([
        ('ox', 'OX Phê duyệt'),
        ('pm', 'PM phê duyệt'),
        ('td', 'TD phê duyệt'),
        ('sd', 'SD phê duyệt'),
        ('ce', 'CE phê duyệt')
        ],default = 'pm',  string='Cấp phê duyệt', index=True, store=True)
    @api.model
    def create(self,vals):
        vals["name"] = vals["level"].upper()
        return super(CompanyApprovalLevel,self).create(vals)