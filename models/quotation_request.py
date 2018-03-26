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


class CostCenterRequest(models.Model):
    _name = 'hr.expense_approval.request_cost_center'
    _description = u'Yêu cầu thanh toán cho từng mã dự toán'
    #_inherit = ['mail.thread']
    request_quotation = fields.Many2one('hr.expense_approval.request_quotation',string='Đề xuất dự toán')

    name = fields.Char(string='Mã dự toán')
    cost_center_id = fields.Many2one('hr.expense_approval.cost_center_code',string="Mã dự toán",onchange='_get_avaiable_amount',required=True)
    cost_center_desc = fields.Char(string='Nội dung mã dự toán',compute='_get_avaiable_amount',readonly=True)
    amount = fields.Float(string='Số tiền', required=True)
    amount_vnd = fields.Float(string='Số tiền (VNĐ)',compute='_set_amount_vnd',store=True)
    currency_rate = fields.Float(string="Tỷ giá",default=1,store=True)
    avaiable_amount = fields.Float(string = "Số còn khả dụng (VNĐ)", compute='_get_avaiable_amount',readonly=True)
    payment_date = fields.Date(string="Ngày đề nghị thanh toán",readonly=True, compute='_get_payment_date', onchange='_get_avaiable_amount')

    @api.depends('request_quotation','request_quotation.payment_date')
    def _get_payment_date(self):
        for request in self:
            request.payment_date = request.request_quotation.payment_date

    @api.depends('currency_rate','amount')
    def _set_amount_vnd(self):
        for request in self:
            request.amount_vnd = request.amount * request.currency_rate

    @api.depends('cost_center_id','payment_date')
    def _get_avaiable_amount(self):
        for request in self:
            request.cost_center_desc= request.cost_center_id.description
            request.name = request.cost_center_id.name
            request.avaiable_amount = 0
            # quotation = self.env['hr.expense_approval.request_quotation'].search([('id','=',self.request_quotation.id)])
            #_logger.debug('Quotation' + str(quotation))
            #if(quotation):
            #    request.payment_date = quotation.payment_date
            if(request.cost_center_id and request.payment_date):  
                avaiable_url = 'http://training.kehoach.osscar.topica.vn/api/ApiBoardChiPhi/CanPay'
                datepayment = datetime.strptime(request.payment_date, "%Y-%m-%d")
                avaiable_params = {
                                        'cdt':request.cost_center_id.cost_center.name,
                                        'ma_du_toan':request.cost_center_id.name,
                                        'thang': datepayment.year * 10 + datepayment.month,
                                        'so_tien':0
                                }
                r = requests.post(url = avaiable_url, data = avaiable_params)
                response_data_a = json.loads(json.dumps(json.loads(r.content)))
                request.avaiable_amount = float(response_data_a["outValue"])
    

class QuotationRequest(models.Model):
    # _inherit = ['mail.thread', 'ir.needaction_mixin']
    _name ="hr.expense_approval.request_quotation"
    _description = u"Đề xuất sử dụng dự toán"
    _order = 'payment_date desc, id desc'

    name = fields.Char(string="Đề xuất",required=True, copy=False, readonly=True, index=True, default='New')
    description=fields.Text(string='Nội dung đề xuất'
            , states={'confirmed': [('readonly', True)], 'approved': [('readonly', True)], 'done': [('readonly', True)]}
        )
    
    financial_activity = fields.Many2one('hr.expense_approval.financial_activity',string="Hoạt động Tài chính",store=True)
    financial_activity_desc = fields.Text(compute='_set_financial_activity')
    cost_center_requests = fields.One2many(
                'hr.expense_approval.request_cost_center'
                , 'request_quotation'
                , string='Yêu cầu mã dự toán'
                , onchange='_get_total_request_amount'
                , states={'confirmed': [('readonly', True)], 'approved': [('readonly', True)], 'done': [('readonly', True)]}
                , ondelete="cascade", copy=False)
    #Ngày đề nghị
    payment_date = fields.Date(default=fields.Date.context_today, string="Ngày đề nghị thanh toán"
                , states={'confirmed': [('readonly', True)], 'approved': [('readonly', True)], 'done': [('readonly', True)]}
                , required=True)
    
    #Người đề nghị
    # , track_visibility='onchange'
    employee_id =fields.Many2one('res.users', string='Người yêu cầu', index=True, default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one('res.company', string='Công ty'
                , states={'confirmed': [('readonly', True)], 'approved': [('readonly', True)], 'done': [('readonly', True)]}
                , default=lambda self: self.env.user.company_id, store=True)
    
    location_id = fields.Many2one('hr.expense_approval.location'
                , string="Địa điểm"
                , states={'confirmed': [('readonly', True)], 'approved': [('readonly', True)], 'done': [('readonly', True)]}
                , required=True,store=True)

    #Số tiền
    currency_id = fields.Many2one('res.currency', string='Tiền tệ thanh toán'
                , states={'confirmed': [('readonly', True)], 'approved': [('readonly', True)], 'done': [('readonly', True)]}
                , default=lambda self: self.env.user.company_id.currency_id)
    total_amount = fields.Float(string='Số tiền', readonly=True, store=True, compute='_get_total_request_amount')
    currency_rate = fields.Float(string="Tỷ giá"
                , states={'confirmed': [('readonly', True)], 'approved': [('readonly', True)], 'done': [('readonly', True)]}
                , default=1)
    total_amount_vnd = fields.Float(string='Số tiền (VND)', store=True, compute='_compute_amount_vnd')
    total_amount_text = fields.Char(string='Số tiền (VND) bằng chữ')
    
    #Approval
    approval_level = fields.Many2one('hr.expense_approval.cost_center_level',string='Cấp phê duyệt', compute='_set_approval_level',readonly=True)
    approval_level_next = fields.Selection([
        ('ox','OX'),
        ('pm', 'PM'),
        ('td', 'TD'),
        ('sd', 'SD'),
        ('ce', 'CE')
        ], default='pm', string='Trạng thái',store=True)
    approval_next =  fields.Many2one('res.users', string="Người duyệt", compute='_compute_cost_center_amount', readonly=True,store=True)
    # financial_level = fields.Many2one('hr.expense_approval.company_level',string='Cấp phê duyệt tài chính', compute='_set_financial_level',readonly=True,store=True)

    #company_financial_approval = fields.Many2one('hr.expense_approval.company')
    #approval_list = fields.Char(string = "Danh sách phê duyệt", compute='_set_approval_level',store=True)

    cost_center_pm = fields.Many2one('res.users', string="Phê duyệt cấp PM"
                , states={'confirmed': [('readonly', True)], 'approved': [('readonly', True)], 'done': [('readonly', True)]}
                ,store=True)
    cost_center_td = fields.Many2one('res.users'
                , states={'approved': [('readonly', True)], 'done': [('readonly', True)]}
                , string="Phê duyệt cấp TD",store=True)
    cost_center_sd = fields.Many2one('res.users', string="Phê duyệt cấp SD",store=True
            , states={'approved': [('readonly', True)], 'done': [('readonly', True)]}
    )
    cost_center_ce = fields.Many2one('res.users', string="Phê duyệt cấp CE",store=True
            , states={'approved': [('readonly', True)], 'done': [('readonly', True)]})
    cost_center_ceo = fields.Many2one('res.users', string="Giám đốc",store=True
            , states={'approved': [('readonly', True)], 'done': [('readonly', True)]})

    #cost_center_approved = fields.Many2many('res.users')
    cost_center_pm_approved = fields.Many2one('res.users', string="Cấp PM",store=True,readonly=True)
    cost_center_td_approved = fields.Many2one('res.users', string="Cấp TD",store=True,readonly=True)
    cost_center_sd_approved= fields.Many2one('res.users', string="Cấp SD",store=True,readonly=True)
    cost_center_ce_approved = fields.Many2one('res.users', string="Cấp CE",store=True,readonly=True)
    cost_center_ceo_approved = fields.Many2one('res.users', string="Giám đốc",store=True,readonly=True)

    fi_ox = fields.Many2one('res.users', string="Phê duyệt cấp OX"
        , states={'done': [('readonly', True)]}
    )
    fi_plan_approver_id = fields.Many2one('res.users', string="Phê duyệt cấp Kế hoạch")
    

    payment_request_id = fields.Char(string="Payment Request", readonly=True)
	
    attachments = fields.Many2many(
                comodel_name="ir.attachment", relation="request_quotation_ir_attachment_relation",
		        column1="quotation_id", column2="attachment_id", string="Hồ sơ, chứng từ"
                , states={'confirmed': [('readonly', True)], 'approved': [('readonly', True)], 'done': [('readonly', True)]})
    template_attachments = fields.Many2many(
                      "hr.expense_approval.financial_activity_document", string="Biểu mẫu, quy trình",store=False,readonly=True)

    state = fields.Selection([
        ('draft', 'Bản draft'),
        ('confirmed', 'Chủ dự toán duyệt'),
        ('approved', 'Tài chính duyệt'),
        ('done', 'Hoàn thành')
        ], default='draft', string='Trạng thái', copy=False, index=True, readonly=True, store=True,
        help="Trạng thái của yêu cầu")

    @api.model
    def create(self, vals):
        # template_obj = self.env['mail.template'].sudo().search([('name','=','create_email_template')], limit=1)
        # for request in self
        #     template_obj.send_mail(request)
        _logger.info('Send mail')
        #self.send_mail_template('request_quotation.new')

        if vals.get('name', 'New') == 'New':  
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.expense_approval.request_quotation') or 'New'
	
        result = super(QuotationRequest, self).create(vals)
        return result

    @api.depends('financial_activity')
    def _set_financial_activity(self):
        for request in self:
            request.financial_activity_desc = request.financial_activity.description
    @api.depends('cost_center_requests')
    def _get_total_request_amount(self):
        for request in self:
            _total_amount = 0
            for line in request.cost_center_requests:
                #line.update({'avaiable_amount':100000})
                _total_amount += line.amount
                request.cost_center_td = line.cost_center_id.cost_center.td
                request.cost_center_sd = line.cost_center_id.cost_center.sd
                request.cost_center_ce = line.cost_center_id.cost_center.ce

            _logger.info('Total amount ', str(_total_amount))
            request.total_amount = _total_amount
    
    @api.depends('total_amount_vnd')
    def _set_approval_level(self):
        for request_quotation in self:
            list_level = self.env['hr.expense_approval.cost_center_level'].search([])
            for level in list_level:
                if(level.from_amount < request_quotation.total_amount_vnd and (level.to_amount == 0 or level.to_amount >= request_quotation.total_amount_vnd)):
                    request_quotation.approval_level = level
    @api.multi
    def action_draft(self):
        self.state = 'draft'
        for request in self.cost_center_requests:
            avaiable_url = 'http://training.kehoach.osscar.topica.vn/api/ApiDBF100/DeletePending'
            datepayment = datetime.strptime(request.payment_date, "%Y-%m-%d")
            avaiable_params = {
                                    'so_serial':self.name+ str(request.id),
                                    'tendangnhap':'hainv2@topica.edu.vn',
                                    'loaif100':'F100'
                            }
            r = requests.post(url = avaiable_url, data = avaiable_params)
            _logger.info('Delete F100: ' + str(r.content))

    @api.multi
    def action_confirm(self):
        _logger.info('START CONFIRM')
        for request in self:
            request.cost_center_pm_approved = None
            request.cost_center_td_approved = None
            request.cost_center_sd_approved = None
            request.cost_center_ce_approved = None
            _logger.info('COST CENTER PM')# + (str)request.cost_center_pm)
            request.state = 'confirmed'
            if(request.cost_center_pm):
                request.approval_next = request.cost_center_pm
                request.approval_level_next = 'pm'
                return
            if(request.cost_center_td):
                request.approval_next = request.cost_center_td
                request.approval_level_next = 'td'
                return 
            if(request.cost_center_sd):
                request.approval_next = request.cost_center_sd
                request.approval_level_next = 'sd'
                return 
            if(request.cost_center_ce):
                request.approval_next = request.cost_center_ce
                request.approval_level_next = 'ce'
                return     

    @api.multi
    def action_quotation_send(self):
        return True

    @api.multi
    def send_mail_template(self,template_id):
        # Find the e-mail template
        template_id = 'hr_expense_approval.request_quotation_'+template_id

        template = self.env.ref(template_id)#'new')
        # Send out the e-mail template to the user
        #for request in self:
        self.env['mail.template'].browse(template.id).send_mail(self.id)#receiver_id)
        _logger.info('Send mail')
        
    @api.multi
    def action_approve(self):
        if(self.approval_next.id != self.env.uid):
            return True

                
        if(self.approval_level.level == self.approval_level_next):
            _logger.info('CAP PHE DUYET CUOI CUNG')
            self.state = 'approved'
        else:
            _logger.info('send mail for next approval')
            self.send_mail_template('approve')#'hr_expense_approval.request_quotation_new',self.approval_next.id)
            
        if(self.approval_level_next == 'pm'):
            self.cost_center_pm_approved = self.approval_next
            if(self.cost_center_td):
                self.approval_next = self.cost_center_td
                self.approval_level_next = 'td'
                return 
            if(self.cost_center_sd):
                self.approval_next = self.cost_center_sd
                self.approval_level_next = 'sd'
                return 
            if(self.cost_center_ce):
                self.approval_next = self.cost_center_ce
                self.approval_level_next = 'ce'
                return
        if(self.approval_level_next == 'td'):
            self.cost_center_td_approved = self.approval_next
            if(self.cost_center_sd):
                self.approval_next = self.cost_center_sd
                self.approval_level_next = 'sd'
                return 
            if(self.cost_center_ce):
                self.approval_next = self.cost_center_ce
                self.approval_level_next = 'ce'
                return
        if(self.approval_level_next == 'sd'):
            self.cost_center_sd_approved = self.approval_next
            if(self.cost_center_ce):
                self.approval_next = self.cost_center_ce
                self.approval_level_next = 'ce'
                return
        if(self.approval_level_next == 'ce'):
            self.cost_center_ce_approved = self.approval_next
   
    @api.multi
    def action_done(self):
        if(self.fi_ox.id != self.env.uid):
            return True

        #TRU DU TOAN
        for request in self.cost_center_requests:
            avaiable_url = 'http://training.kehoach.osscar.topica.vn/api/ApiDBF100/CreatePending'
            datepayment = datetime.strptime(request.payment_date, "%Y-%m-%d")
            avaiable_params = {
                                    'cdt':request.cost_center_id.cost_center.name,
                                    'mdt':request.cost_center_id.name,
                                    'thang': datepayment.year * 10 + datepayment.month,
                                    'soTien':request.amount_vnd,
                                    'ngayDeNghiThanhToan':self.payment_date,
                                    'noiDung':self.description ,
                                    'serialNumber':self.name + str(request.id),
                                    'ky':'de6984a1728e4fe89da0b4e1862d7839',
                                    'tenDangNhap':'hainv2@topica.edu.vn',
                                    'loaif100':'F100'
                            }
            r = requests.post(url = avaiable_url, data = avaiable_params)
            _logger.info('Create F100: ' + str(avaiable_params))
            _logger.info('Create F100: ' + str(r.content))
        self.state = 'done'
       
    
    @api.depends('total_amount', 'currency_id','currency_rate')
    def _compute_amount_vnd(self):
        for request_quotation in self:
            request_quotation.total_amount_vnd = request_quotation.total_amount * request_quotation.currency_rate
