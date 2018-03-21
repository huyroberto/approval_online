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
        self.state = 'confirmed'
        self.cost_center_pm_approved = None
        self.cost_center_td_approved = None
        self.cost_center_sd_approved = None
        self.cost_center_ce_approved = None
        if(self.cost_center_pm):
            self.approval_next = self.cost_center_pm
            self.approval_level_next = 'pm'
            return
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

<<<<<<< HEAD
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
        
=======
>>>>>>> 83cb92b662bff3561e27e4136fda45bf04155901
    @api.multi
    def action_quotation_send(self, rec_id):
    
        template = self.env['ir.model.data'].get_object('mail_template_demo', 'example_email_template')

        # Send out the e-mail template to the user
        self.env['mail.template'].browse(template.id).send_mail(rec_id)
        
        return True
        
    @api.multi
    def action_approve(self):
<<<<<<< HEAD
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
=======
        if(self.approval_next.id != self.env.uid):
            return True
        
        if(self.approval_level.level == self.approval_level_next):
            _logger.info('CAP PHE DUYET CUOI CUNG')
            self.state = 'approved'
        
        if(self.approval_level_next == 'pm'):
            self.cost_center_pm_approved = self.approval_next
            if(self.cost_center_td):
                self.approval_next = self.cost_center_td
>>>>>>> 83cb92b662bff3561e27e4136fda45bf04155901
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
<<<<<<< HEAD
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
=======
            request_quotation.total_amount_vnd = request_quotation.total_amount * request_quotation.currency_rate
>>>>>>> 83cb92b662bff3561e27e4136fda45bf04155901
