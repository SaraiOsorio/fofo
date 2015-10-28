# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015-Today Ecosoft Co., Ltd. (http://Ecosoft.co.th).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from openerp import models, fields, api, _
from openerp.exceptions import Warning


class sales_refund_report(models.TransientModel):
    _name = 'sale.refund.report'
    
    @api.multi
    def _get_fiscalyear(self):
        if self.env.context is None:
            self.env.context = {}
        now = time.strftime('%Y-%m-%d')
        company_id = False
        ids = self.env.context.get('active_ids', [])
        if ids and self.env.context.get('active_model') == 'account.account':
            company_id = self.env['account.account'].browse(ids[0]).company_id.id
        else:  # use current company id
            company_id = self.env.user.company_id.id
        domain = [('company_id', '=', company_id), ('date_start', '<', now), ('date_stop', '>', now)]
        fiscalyears = self.env['account.fiscalyear'].search(domain, limit=1).ids
        return fiscalyears and fiscalyears[0] or False
    
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env['res.company']._company_default_get('fofo.sale.report'))
    fiscalyear_id = fields.Many2one('account.fiscalyear', string='Fiscal Year', default = _get_fiscalyear)
    filter = fields.Selection([('filter_no', 'No Filters'), 
                               ('filter_date', 'Date'), 
                               ('filter_period', 'Periods')], "Filter by", default='filter_no',required=True)
    date_from = fields.Date('Start Date')
    date_to = fields.Date('End Date')
    period_from = fields.Many2one('account.period', 'Start Period')
    period_to = fields.Many2one('account.period', 'End Period')
    customer_ids = fields.Many2many('res.partner', string='Customer')
    
    @api.constrains('fiscalyear_id','period_from','period_to')
    def _check_company_id(self):
        for wiz in self:
            company_id = wiz.company_id.id
            if wiz.fiscalyear_id and company_id != wiz.fiscalyear_id.company_id.id:
                raise Warning(_('Warning'),_('The fiscalyear, periods or chart of account chosen have to belong to the same company.'))
            if wiz.period_from and company_id != wiz.period_from.company_id.id:
                raise Warning(_('Warning'),_('The fiscalyear, periods or chart of account chosen have to belong to the same company.'))
            if wiz.period_to and company_id != wiz.period_to.company_id.id:
                raise Warning(_('Warning'),_('The fiscalyear, periods or chart of account chosen have to belong to the same company.'))
    
    @api.onchange('filter')
    def onchange_filter(self):
        if self.filter == 'filter_no':
            self.date_from = False
            self.date_to = False
            self.period_from = False
            self.period_to = False
        if self.filter == 'filter_date':
            self.date_from = time.strftime('%Y-01-01')
            self.date_to = time.strftime('%Y-%m-%d')
            self.period_from = False
            self.period_to = False
        if self.filter == 'filter_period' and self.fiscalyear_id:
            start_period = end_period = False
            self._cr.execute('''
                SELECT * FROM (SELECT p.id
                               FROM account_period p
                               LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
                               WHERE f.id = %s
                               AND p.special = false
                               ORDER BY p.date_start ASC, p.special ASC
                               LIMIT 1) AS period_start
                UNION ALL
                SELECT * FROM (SELECT p.id
                               FROM account_period p
                               LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
                               WHERE f.id = %s
                               AND p.date_start < NOW()
                               AND p.special = false
                               ORDER BY p.date_stop DESC
                               LIMIT 1) AS period_stop''', (self.fiscalyear_id.id, self.fiscalyear_id.id))
            periods =  [i[0] for i in self._cr.fetchall()]
            if periods and len(periods) > 1:
                start_period = periods[0]
                end_period = periods[1]
            self.date_from = False
            self.date_to = False
            self.period_from = start_period
            self.period_to = end_period
                
    @api.model
    def _build_contexts(self, data):
        if self.env.context is None:
            self.env.context = {}
        result = {}
        result['fiscalyear'] = 'fiscalyear_id' in data['form'] and data['form']['fiscalyear_id'] or False
        result['customer_ids'] = 'customer_ids' in data['form'] and data['form']['customer_ids'] or False
        result['company_id'] = 'company_id' in data['form'] and data['form']['company_id'] or False
        if data['form']['filter'] == 'filter_date':
            result['date_from'] = data['form']['date_from']
            result['date_to'] = data['form']['date_to']
        elif data['form']['filter'] == 'filter_period':
            if not data['form']['period_from'] or not data['form']['period_to']:
                raise Warning(_('Error!'),_('Select a starting and an ending period.'))
            result['period_from'] = data['form']['period_from']
            result['period_to'] = data['form']['period_to']
        return result
                
    @api.multi
    def print_report(self, data):
        if self.env.context is None:
            self.env.context = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from',  'date_to', 'customer_ids','company_id', 'fiscalyear_id', 'period_from', 'period_to',  'filter'])[0]
        for field in ['fiscalyear_id', 'period_from', 'period_to']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        used_context = self._build_contexts(data)
        data['form']['periods'] = used_context.get('periods', False) and used_context['periods'] or []
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang', 'en_US'))
        return self.pool['report'].get_action(self._cr, self._uid, [], 'fofo_sales_report.fofo_sales_refund_report', data=data, context=self.env.context)#probuse


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
