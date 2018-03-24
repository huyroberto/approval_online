# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models
from datetime import datetime
import logging
import requests
import httplib, urllib
import json
_logger = logging.getLogger(__name__)

class CostCenterPaymentRequest(models.Model):
    _name = 'hr.expense_approval.request_cost_center_payment'
    _description = u'Yêu cầu thanh toán cho từng mã dự toán'
    request_payment = fields.Many2one('hr.expense_approval.request_payment',string='Thanh toán dự toán')

    name = fields.Char(string='Mã dự toán')
    cost_center_id = fields.Many2one('hr.expense_approval.cost_center_code',string="Mã dự toán",onchange='_get_avaiable_amount',required=True)
    cost_center_desc = fields.Char(string='Nội dung mã dự toán',compute='_get_avaiable_amount',readonly=True)
    amount = fields.Float(string='Số tiền', readonly=True,store=True,compute='_get_avaiable_amount')
    amount_vnd = fields.Float(string='Số tiền (VNĐ)',compute='_get_avaiable_amount', store=True)
    avaiable_amount = fields.Float(string = "Số còn khả dụng (VNĐ)", compute='_get_avaiable_amount',readonly=True, store=True)
    payment_date = fields.Date(string="Ngày đề nghị thanh toán",readonly=True, compute='_get_payment_date', onchange='_get_avaiable_amount')

    @api.depends('request_payment','request_payment.payment_date')
    def _get_payment_date(self):
        return
        #for request in self:

            #request.payment_date = request.request_payment.payment_date

    @api.depends('cost_center_id','payment_date')
    def _get_avaiable_amount(self):
        for request in self:
            request.payment_date = request.request_payment.quotation_id.payment_date
            request.amount = 0
            # cost_center_request = None
            for cost_center in request.request_payment.quotation_id.cost_center_requests:
                if(cost_center.cost_center_id == request.cost_center_id):
                    request.amount = cost_center.amount
                    break
                
            request.cost_center_desc= request.cost_center_id.description
            request.name = request.cost_center_id.name
            
            request.avaiable_amount = 0
            # quotation = self.env['hr.expense_approval.request_quotation'].search([('id','=',self.request_quotation.id)])
            #_logger.debug('Quotation' + str(quotation))
            #if(quotation):
            #request.payment_date = quotation.payment_date
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

    payment_amount = fields.Float(string ='Số tiền thanh toán',required=True, store=True)
    payment_amount_vnd = fields.Float(string ='Số tiền thanh toán (VNĐ)', readonly=True, store=True)

class PaymentRequest(models.Model):
    _name = "hr.expense_approval.request_payment"
    _description = "Yeu cau thanh toan"
    name = fields.Char(string="Yêu cầu thanh toán", required=True, copy=False, readonly=True,index=True, default='New')
    description = fields.Text(string="Nội dung",readonly=True, compute='_onchange_quotation_id')

     #Ngày đề nghị
    date = fields.Date(default=fields.Date.context_today, string="Ngày yêu cầu",readonly=True)
    payment_date = fields.Date(string="Ngày đề nghị thanh toán",store=True, readonly=True,compute='_onchange_quotation_id')
    financial_activity = fields.Many2one('hr.expense_approval.financial_activity',string="Hoạt động Tài chính",readonly=True, compute='_onchange_quotation_id')
    #Người đề nghị
    employee_id = fields.Many2one('res.users', string="Người yêu cầu", index=True, readonly=True, compute='_onchange_quotation_id')
    company_id = fields.Many2one('res.company', string='Công ty', readonly=True, compute='_onchange_quotation_id')
    location_id = fields.Many2one('hr.expense_approval.location', string="Địa điểm",readonly=True, compute='_onchange_quotation_id')

     #quotation request
    quotation_id = fields.Many2one('hr.expense_approval.request_quotation',
                                          string='Đề xuất dự toán')
    cost_center_payment_requests = fields.One2many(
                'hr.expense_approval.request_cost_center_payment'
                , 'request_payment'
                , string='Yêu cầu mã dự toán'
                #, onchange='_get_total_request_amount'
                , states={'confirmed': [('readonly', True)], 'approved': [('readonly', True)], 'done': [('readonly', True)], 'closed': [('readonly', True)]}
                , ondelete="cascade", copy=False)
    
    
    #Amount
    #Số tiền
    currency_id = fields.Many2one('res.currency', string='Tiền tệ thanh toán',readonly=True ,compute='_onchange_quotation_id')
    currency_rate = fields.Float(string="Tỷ giá", compute='_onchange_quotation_id', store=True)
    #total_amount = fields.Float(string='Đề xuất', readonly=True)
    #total_amount_vnd = fields.Float(string='Đề xuất(VND)', store=True, compute='_compute_amount_vnd')
    total_payment_amount = fields.Float(string='Thanh toán',  compute='_get_total_request_amount', readonly=True, store=True)
    total_payment_amount_vnd = fields.Float(string='Thanh toán (VND)',compute='_compute_amount_vnd', readonly = True, store=True)
    #total_amount_text = fields.Char(string='Đề xuất(VND) bằng chữ',readonly=True)

    total_line_cash_amount = fields.Float(string='Tiền mặt', compute='_compute_totalAmount', store=True, readonly=True)
    total_line_bank_amount = fields.Float(string='Chuyển khoản ngân hàng', compute='_compute_totalAmount', store=True, readonly=True)


    attachments = fields.Many2many(
                      comodel_name="ir.attachment", relation="request_quotation_ir_attachment_relation",
		       column1="quotation_id", column2="attachment_id", string="Hồ sơ, chứng từ")
    
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


    fi_ox = fields.Many2one('res.users', string="OX phụ trách"
                , readonly=True
                , compute='_onchange_quotation_id'
                ,store=True)
    fi_pm = fields.Many2one('res.users', string="Phê duyệt cấp PM"
                , readonly=True
                , compute='_onchange_quotation_id'
                ,store=True)
    fi_td = fields.Many2one('res.users'
                , readonly=True
                , compute='_onchange_quotation_id'
                , string="Phê duyệt cấp TD",store=True)
    fi_sd = fields.Many2one('res.users', string="Phê duyệt cấp SD",store=True
            , compute='_onchange_quotation_id'
            , readonly=True
    )
    fi_ce = fields.Many2one('res.users', string="Phê duyệt cấp CE",store=True
            , compute='_onchange_quotation_id'
            , readonly=True)
    fi_ceo = fields.Many2one('res.users', string="Giám đốc",store=True
            , readonly=True)

    #cost_center_approved = fields.Many2many('res.users')
    fi_ox_approved = fields.Many2one('res.users', string="Cấp OX",store=True,readonly=True)
    fi_pm_approved = fields.Many2one('res.users', string="Cấp PM",store=True,readonly=True)
    fi_td_approved = fields.Many2one('res.users', string="Cấp TD",store=True,readonly=True)
    fi_sd_approved= fields.Many2one('res.users', string="Cấp SD",store=True,readonly=True)
    fi_ce_approved = fields.Many2one('res.users', string="Cấp CE",store=True,readonly=True)
    fi_ceo_approved = fields.Many2one('res.users', string="Giám đốc",store=True,readonly=True)

    approval_level = fields.Many2one('hr.expense_approval.cost_center_level',string='Cấp phê duyệt', compute='_set_approval_level',readonly=True, store=True)
    fi_approval_level = fields.Many2one('hr.expense_approval.company_level',string='Cấp phê duyệt', compute='_set_approval_level',readonly=True, store=True)
    approval_next =  fields.Many2one('res.users', string="Người phê duyệt tiếp", compute='_compute_cost_center_amount', readonly=True,store=True)
     #Approval
    approval_level_next = fields.Selection([
        ('ox','OX'),
        ('pm', 'PM'),
        ('td', 'TD'),
        ('sd', 'SD'),
        ('ce', 'CE')
        ], default='pm', string='Trạng thái',store=True)

    #Line
    expense_line_ids = fields.One2many('hr.expense_approval.request_payment.line', 'payment_id',
                                       string="Các lịch thanh toán",ondelete="cascade", copy=False)
    
    #Status - BEGIN
    payment_type = fields.Selection([
        ('payment', 'Thanh toán'),
        ('temp', 'Tạm ứng')
        ], default='payment',  string='Loại', copy=False, index=True,store=True)

    state = fields.Selection([
        ('draft', 'Bản drafft'),
        ('confirmed', 'Chủ dự toán duyệt'),
        ('approved', 'Tài chính duyệt'),
        ('done', 'Hoàn thành')
        ], default='draft',  string='Trạng thái', copy=False, index=True, readonly=True, store=True,
        help="Status of the request.")

    @api.depends('total_payment_amount_vnd')
    def _set_approval_level(self):
        for request in self:
            list_level = self.env['hr.expense_approval.cost_center_level'].search([])
            for level in list_level:
                if(level.from_amount < request.total_payment_amount_vnd and
                   (level.to_amount == 0 or level.to_amount >= request.total_payment_amount_vnd)):
                    request.approval_level = level

            list_company_level = self.env['hr.expense_approval.company_level'].search([])
            for level in list_company_level:
                if(level.from_amount < request.total_payment_amount_vnd and
                   (level.to_amount == 0 or level.to_amount >= request.total_payment_amount_vnd)):
                    request.fi_approval_level = level

    @api.depends('cost_center_payment_requests')
    def _get_total_request_amount(self):
        for request in self:
            _total_amount = 0
            for line in request.cost_center_payment_requests:
                #line.update({'avaiable_amount':100000})
                _total_amount += line.payment_amount

            _logger.info('Total amount ', str(_total_amount))
            request.update({'total_payment_amount':_total_amount})
            
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.expense_approval.request_payment') or 'New'

        result = super(PaymentRequest, self).create(vals)
        return result

    @api.multi
    def action_draft(self):
        self.state = 'draft'

    @api.multi
    def action_confirm(self):
        for request in self:
            request.cost_center_pm_approved = None
            request.cost_center_td_approved = None
            request.cost_center_sd_approved = None
            request.cost_center_ce_approved = None
            _logger.info('COST CENTER PM: ' + str( request.cost_center_pm))
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
    def action_approve(self):
        if(self.approval_next.id != self.env.uid):
            return True
        
        if(self.approval_level.level == self.approval_level_next):
            _logger.info('CAP PHE DUYET CUOI CUNG')
            self.approval_next = self.quotation_id.fi_ox
            self.state = 'approved'
            self.fi_pm_approved = None
            self.fi_td_approved = None
            self.fi_sd_approved = None
            self.fi_ce_approved = None
            if(self.fi_pm):
                self.approval_next = self.fi_pm
                self.approval_level_next = 'pm'
                return
            if(self.fi_td):
                self.approval_next = self.fi_td
                self.approval_level_next = 'td'
                return 
            if(self.fi_sd):
                self.approval_next = self.fi_sd
                self.approval_level_next = 'sd'
                return 
            if(self.fi_ce):
                self.approval_next = self.fi_ce
                self.approval_level_next = 'ce'
                return     
        
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
        if(self.approval_next.id != self.env.uid):
            return True
        
        if(self.fi_approval_level.level == self.approval_level_next):
            _logger.info('CAP PHE DUYET CUOI CUNG')
            for request in self.cost_center_payment_requests:
                avaiable_url = 'http://training.kehoach.osscar.topica.vn/api/ApiDBF100/CreatePending'
                datepayment = datetime.strptime(request.payment_date, "%Y-%m-%d")
                avaiable_params = {
                                        'soSerial':self.quotation_id.name + str(request.id),
                                        'count':1,
                                        'email':'hainv2@topica.edu.vn',
                                        'loaif100':'F100'
                                }
                r = requests.post(url = avaiable_url, data = avaiable_params)
                _logger.info('Create F100: ' + str(r.content))
            self.state = 'done'
        
        if(self.approval_level_next == 'pm'):
            self.fi_pm_approved = self.approval_next
            if(self.fi_td):
                self.fi_approval_next = self.fi_td
                self.approval_level_next = 'td'
                return 
            if(self.fi_sd):
                self.approval_next = self.fi_sd
                self.approval_level_next = 'sd'
                return 
            if(self.fi_ce):
                self.approval_next = self.fi_ce
                self.approval_level_next = 'ce'
                return
        if(self.fi_approval_level_next == 'td'):
            self.fi_td_approved = self.approval_next
            if(self.fi_sd):
                self.approval_next = self.fi_sd
                self.approval_level_next = 'sd'
                return 
            if(self.fi_ce):
                self.approval_next = self.fi_ce
                self.approval_level_next = 'ce'
                return
        if(self.fi_approval_level_next == 'sd'):
            self.fi_sd_approved = self.approval_next
            if(self.fi_ce):
                self.approval_next = self.fi_ce
                self.approval_level_next = 'ce'
                return
        if(self.approval_level_next == 'ce'):
            self.fi_ce_approved = self.approval_next

    #@api.onchange('quotation_id')
    @api.depends('quotation_id')
    def _onchange_quotation_id(self):
        for payment in self:
            
            payment.description =  payment.quotation_id.description
            payment.payment_date = payment.quotation_id.payment_date
            payment.employee_id = payment.quotation_id.employee_id
            payment.company_id = payment.quotation_id.company_id
            payment.location_id  = payment.quotation_id.location_id.id
            
            #payment.name = payment.quotation_id.name
            payment.financial_activity = payment.quotation_id.financial_activity.id
            payment.currency_id = payment.quotation_id.currency_id.id
            payment.currency_rate = payment.quotation_id.currency_rate

            payment.cost_center_pm = payment.quotation_id.cost_center_pm
            payment.cost_center_td = payment.quotation_id.cost_center_td
            payment.cost_center_sd = payment.quotation_id.cost_center_sd
            payment.cost_center_ce = payment.quotation_id.cost_center_ce

            payment.fi_ox = payment.quotation_id.cost_center_pm#fi_ox
            

            #REFRESH LIST COST_CENTER_PAYMENT_REQUEST
            #payment.cost_center_payment_requests = None
            
            #SET APPROVAL
            company_info = self.env['hr.expense_approval.company'].search([('company','=',payment.quotation_id.company_id.id)])
            _logger.info('Company: ' + str(company_info))
            payment.fi_pm = company_info.pm
            payment.fi_td = company_info.td
            payment.fi_sd = company_info.sd
            payment.fi_ce = company_info.ce


    @api.depends('currency_rate','total_payment_amount')
    def _compute_amount_vnd(self):
        for request in self:
                #request.total_amount_vnd = request.total_amount * request.currency_rate
                request.update({'total_payment_amount_vnd' : request.total_payment_amount * request.currency_rate})

    # @api.multi
    # def action_draft(self):
    #     self.state = 'draft'

    # @api.multi
    # def action_confirm(self):
    #     self.state = 'confirmed'

    # @api.multi
    # def action_approve(self):
    #     self.state = 'approved'

    # @api.multi
    # def action_done(self):
    #     self.state = 'done'

    @api.depends('expense_line_ids.bank_amount','expense_line_ids.cash_amount')
    #@api.onchange('expense_line_ids')
    def _compute_totalAmount(self):
        for request in self:
            total_cash = total_bank = 0.0
            for line in request.expense_line_ids:
                #_logger.info('Payment Line - ' + line.name)
                total_cash += line.cash_amount
                total_bank += line.bank_amount
            request.update({
                'total_line_cash_amount': total_cash,
                'total_line_bank_amount': total_bank
            }) 

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

    # attachments = fields.Many2many(
    #                   comodel_name="ir.attachment", relation="request_quotation_ir_attachment_relation",
	# 	       column1="quotation_id", column2="attachment_id", string="Hồ sơ, chứng từ")
    # @api.multi
    # def _compute_attachment_number(self):
    #     attachment_data = self.env['ir.attachment'].read_group([('res_model', '=', 'hr.expense_approval.request_payment.line'), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
    #     attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
    #     for request_payment in self:
    #         request_payment.attachment_number = attachment.get(request_payment.id, 0)
    # @api.multi
    # def action_get_attachment_view(self):
    #     self.ensure_one()
    #     res = self.env['ir.actions.act_window'].for_xml_id('base', 'action_attachment')
    #     res['domain'] = [('res_model', '=', 'hr.expense_approval.request_payment.line'), ('res_id', 'in', self.ids)]
    #     res['context'] = {'default_res_model': 'hr.expense_approval.request_payment.line', 'default_res_id': self.id}
    #     return res

    @api.depends('cash_amount', 'bank_amount')
    def _compute_total_amount(self):
        for line in self:
            line.total_amount = line.cash_amount + line.bank_amount
    
