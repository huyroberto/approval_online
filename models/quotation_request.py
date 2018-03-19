# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)
#import openerp.http as http
import requests
import httplib, urllib
import json

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
    
    location_id = fields.Many2one('hr.expense_approval.location', string="Địa điểm",required=True,store=True)
    #department_id = fields.Many2one('hr.department', string='Phòng ban', readonly=True, store=True)
    
    #Nguoi huong
    beneficiary = fields.Char(string="Người/Công ty thụ hưởng")

    #Số tiền
    currency_id = fields.Many2one('res.currency', string='Tiền tệ thanh toán', default=lambda self: self.env.user.company_id.currency_id)
    amount = fields.Float(string='Số tiền', required=True)
    currency_rate = fields.Float(string="Tỷ giá",required=True,default=1)
    amount_vnd = fields.Float(string='Số tiền (VND)', store=True, compute='_compute_amount_vnd')
    amount_text = fields.Char(string='Số tiền (VND) bằng chữ')

    #BPMS
    avaiable_amount = fields.Float(string = "Số còn khả dụng", compute='_compute_cost_center_amount',readonly=True)
    real_amount = fields.Float(string = "Số còn thực tế", compute='_compute_cost_center_amount', readonly=True)

    #attachment_number = fields.Integer(compute='_compute_attachment_number', string='Số chứng từ')
    
    #Approval

    approval_level = fields.Many2one('hr.expense_approval.level',string='Cấp phê duyệt chủ dự toán', compute='_set_approval_level',readonly=True,store=True)
    approval_level_next = fields.Selection([
        ('ox','OX'),
        ('pm', 'PM'),
        ('td', 'TD'),
        ('sd', 'SD'),
        ('ce', 'CE')
        ], default='pm', string='Trạng thái',store=True)
    approval_next =  fields.Many2one('hr.employee', string="Người phê duyệt tiếp theo", compute='_compute_cost_center_amount', readonly=True,store=True)
    financial_level = fields.Many2one('hr.expense_approval.financial_level',string='Cấp phê duyệt tài chính', compute='_set_financial_level',readonly=True,store=True)

    company_financial_approval = fields.Many2one('hr.expense_approval.company_financial_approval')
    #approval_list = fields.Char(string = "Danh sách phê duyệt", compute='_set_approval_level',store=True)

    pm_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp PM",store=True)
    td_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp TD",store=True)
    sd_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp SD",store=True)
    ce_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp CE",store=True)
    ceo_approver_id = fields.Many2one('hr.employee', string="Giám đốc",readonly=True,store=True)

    fi_ox_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp OX")
    fi_plan_approver_id = fields.Many2one('hr.employee', string="Phê duyệt cấp Kế hoạch")
    

    payment_request_id = fields.Char(string="Payment Request")
	
    attachments = fields.Many2many(
                      comodel_name="ir.attachment", relation="request_quotation_ir_attachment_relation",
		       column1="quotation_id", column2="attachment_id", string="Hồ sơ, chứng từ")
    template_attachments = fields.Many2many(
                      "ir.attachment", string="Biểu mẫu, quy trình",store=False,readonly=True)

    state = fields.Selection([
        ('draft', 'Bản draft'),
        ('confirmed', 'Chủ dự toán duyệt'),
        ('approved', 'Tài chính duyệt'),
        ('done', 'Chờ thanh toán')
        ], default='draft', string='Trạng thái', copy=False, index=True, readonly=True, store=True,
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

        # Find the e-mail template
        #template = self.env.ref('mail_template_demo.example_email_template')
    
        template = self.env['ir.model.data'].get_object('mail_template_demo', 'example_email_template')

        # Send out the e-mail template to the user
        self.env['mail.template'].browse(template.id).send_mail(self.id)
                                                
        #if self.env.context.get('send_email'):
        #
        #self.force_quotation_send()
     
        #if self.env['ir.values'].get_default('sale.config.settings', 'auto_done_setting'):
        #    self.action_done()
        
    @api.multi
    def action_quotation_send(self, rec_id):
    
        template = self.env['ir.model.data'].get_object('mail_template_demo', 'example_email_template')

        # Send out the e-mail template to the user
        self.env['mail.template'].browse(template.id).send_mail(rec_id)
        
        return True
        
    @api.multi
    def action_approve(self):
        _logger.info('Approve now')
        _logger.info('Next Approver:' + str(self.approval_next.user_id.id ))
        _logger.info('Next Approver:' + str(self.env.uid))
        if(self.approval_next.user_id.id != self.env.uid):
            return {
                    'warning': {
                        'title': 'Warning!',
                        'message': 'The warning text'}
            }
        else:
            # approvers = self.approval_list.split(“|”)
            # for approver in approvers
            #     approver_id = int(approver)
            my_emp_id = int(self.env.uid)
            my_emp = self.env['hr.employee'].search([('user_id', '=', my_emp_id)])
            _logger.info('My Employee ' + str(my_emp))
            _logger.info('PM Approver ' + str(self.pm_approver_id.id))
            #Trangnt: send mail for quotation
            self.acction_quotation_send()
            
            #Lay list approvers cua cost center
            if(self.pm_approver_id.id is False):
                _logger.info('Set PM Approver')
                self.pm_approver_id = my_emp
                self.approval_next = self.cost_center_id.td_approver_id
                self.approval_level_next = 'td'
                return
            if(self.td_approver_id.id is False):
                _logger.info('Set TD Approver')
                self.td_approver_id = my_emp
                if(self.approval_level.level == "td"):
                    self.state = 'approved'
                    self.approval_next = self.company_financial_approval.ox_approver_id
                    self.approval_level_next = 'ox'
                else:
                    self.approval_level_next = 'sd'
                    self.approval_next = self.cost_center_id.sd_approver_id
                return
            if(self.sd_approver_id.id is False):
                _logger.info('Set SD Approver')
                self.sd_approver_id = my_emp
                if(self.approval_level.level == "ce"):
                    self.state = 'approved'
                    self.approval_next = self.company_financial_approval.ox_approver_id
                    self.approval_level_next = 'ox'
                else:
                    self.approval_level_next = 'ce'
                    self.approval_next = self.cost_center_id.ce_approver_id
                return
            if(self.ce_approver_id.id is False):
                _logger.info('Set CE Approver')
                self.ce_approver_id = my_emp
                self.state = 'approved'         
                #Chuyen sang tai chinh duyet
                self.approval_next = self.company_financial_approval.ox_approver_id
                self.approval_level_next = 'ox'
        #approval PM,TD,SD,CE,CEO,
        
    @api.multi
    def action_done(self):
        if(self.approval_next.user_id.id != self.env.uid):
            return
        else:
            my_emp_id = int(self.env.uid)
            my_emp = self.env['hr.employee'].search([('user_id', '=', my_emp_id)])

            self.fi_ox_approver_id = my_emp
            self.state = 'done'

            #Create payment request
            payment = self.env['hr.expense_approval.request_payment'].create({
                    'name': u"Yêu cầu thanh toán - " + self.name,
                    'description': self.name,
                    'date': self.date,
                    'employee_id': self.employee_id.id,
                    'company_id': self.company_id.id,
                    'amount_vnd' : self.amount_vnd,
                    'amount': self.amount,
                    'approval_level' : self.approval_level.id,
                    'cost_center_id' : self.cost_center_id.id,
                    'payment_date' : self.payment_date,
                    'quotation_id' : self.id,
                    'financial_activity' : self.financial_activity.id,
                    'beneficiary' : self.beneficiary,
                    'currency_rate' : self.currency_rate,
                    'location_id' : self.location_id.id,
                    'currency_id' : self.currency_id.id,

            })
        #approval account
    
    @api.depends('amount', 'currency_id','currency_rate')
    def _compute_amount_vnd(self):
        _logger.info("My User ID" + str(self.env.uid))
        for request_quotation in self:
            request_quotation.amount_vnd = request_quotation.amount * request_quotation.currency_rate
    
    @api.depends('amount_vnd','cost_center_id')
    def _set_approval_level(self):
         for request_quotation in self:
            list_level = self.env['hr.expense_approval.level'].search([])
            for level in list_level:
                if(level.from_amount < request_quotation.amount_vnd and (level.to_amount == 0 or level.to_amount >= request_quotation.amount_vnd)):
                    request_quotation.approval_level = level
            list_financial_level = self.env['hr.expense_approval.financial_level'].search([])
            for level in list_financial_level:
                if(level.from_amount < request_quotation.amount_vnd and (level.to_amount == 0 or level.to_amount >= request_quotation.amount_vnd)):
                    request_quotation.financial_level = level

    # @api.multi
    # def _compute_attachment_number(self):
    #     attachment_data = self.env['ir.attachment'].read_group([('res_model', '=', 'hr.expense_approval.request_quotation'), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
    #     attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
    #     for request_quotation in self:
    #         request_quotation.attachment_number = attachment.get(request_quotation.id, 0)
    
    # @api.multi
    # def action_get_attachment_view(self):
    #     self.ensure_one()
    #     res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
    #     res['domain'] = [('res_model', '=', 'hr.expense_approval.request_quotation'), ('res_id', 'in', self.ids)]
    #     res['context'] = {'default_res_model': 'hr.expense_approval.request_quotation', 'default_res_id': self.id}
    #     return res
    
    def _onchange_financial_activity(self):
        self.template_attachments = self.financial_activity.attachments
        self.name = self.cost_center_id.name + " - " + self.financial_activity.name

    #@api.onchange('cost_center_id')
    @api.depends('payment_date','cost_center_id')
    def _compute_cost_center_amount(self):
        if(self.cost_center_id):
            for request_quotation in self:    

                #Next Approval Online
                #Phu thuoc vao cost_center_id
                request_quotation.approval_next = request_quotation.cost_center_id.pm_approver_id
                if(request_quotation.pm_approver_id):
                    request_quotation.approval_next = request_quotation.cost_center_id.td_approver_id
                
                if(request_quotation.td_approver_id and (request_quotation.approval_level.level == "sd" or request_quotation.approval_level.level == "ce")):
                    request_quotation.approval_next = request_quotation.cost_center_id.sd_approver_id

                
                if(request_quotation.sd_approver_id and (request_quotation.approval_level.level == "ce")):
                    request_quotation.approval_next = request_quotation.cost_center_id.ce_approver_id

                _logger.info('Next Approval: ' + str(request_quotation.approval_next))

                #request_quotation.pm_approver_id = request_quotation.cost_center_id.pm_approver_id
                #request_quotation.td_approver_id = request_quotation.cost_center_id.td_approver_id
                #request_quotation.sd_approver_id = request_quotation.cost_center_id.sd_approver_id
                #request_quotation.ce_approver_id = request_quotation.cost_center_id.ce_approver_id
                #request_quotation.ceo_approver_id = request_quotation.cost_center_id.ceo_approver_id

                avaiable_url = 'http://training.kehoach.osscar.topica.vn/api/ApiBoardChiPhi/CanPay'
                real_url = 'http://training.kehoach.osscar.topica.vn/api/ApiBoardChiPhi/MyPresentMoney'
                # int(str
                # (
                # datetime.strftime
                #     (
                #         request_quotation.payment_date,'%Y'
                #     )
                # ) + 
                # str(int(datetime.strftime(request_quotation.payment_date,'%m')))),
                datepayment = datetime.strptime(request_quotation.payment_date, "%Y-%m-%d")
                #_logger.info('Payment Date: '+ str(datepayment.year * 10 + datepayment.month))
                avaiable_params = {
                                        'cdt':request_quotation.cost_center_id.name[:3],
                                        'ma_du_toan':request_quotation.cost_center_id.name,
                                        'thang': datepayment.year * 10 + datepayment.month,
                                        'so_tien':0
                                }
                r = requests.post(url = avaiable_url, data = avaiable_params)
                r_real = requests.post(url = real_url, data = avaiable_params)
                #conn = httplib.HTTPConnection("training.kehoach.osscar.topica.vn:80")
                #conn.request("POST", "/api/ApiBoardChiPhi/CanPay?"+urllib.urlencode(avaiable_params))
                _logger.info('BPMS Request: ' + urllib.urlencode(avaiable_params))
                #r = conn.getresponse()
                response_data_a = json.loads(json.dumps(json.loads(r.content)))
                response_data_r = json.loads(json.dumps(json.loads(r_real.content)))
                _logger.info('BPMS Response: ' + str(response_data_a) + str(response_data_r))
                _logger.info('Out Value: ' + str(response_data_a["outValue"]))
                #if(response_data_a["success"]==1):
                request_quotation.avaiable_amount = float(response_data_a["outValue"])
                request_quotation.real_amount = float(response_data_r["outValue"])
            #else:
            #    request_quotation.avaiable_amount = 0
            #    request_quotation.real_amount = 0
    @api.model
    def create(self,vals):
        vals["quotation_request_id"] = datetime.utcnow().strftime('%Y%m%d.%H%M%S%f')[:-3]
        #vals["name"]= selft.cost_center_id.name + "-" + self.financial_activity.name
        return super(QuotationRequest,self).create(vals)
