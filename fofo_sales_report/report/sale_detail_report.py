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
from datetime import date, time
import datetime

from openerp.osv import osv
from openerp.report import report_sxw

class fofo_sales_detail_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context={}):
        super(fofo_sales_detail_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
                    'get_fiscalyear': self._get_fiscalyear,
                    'get_company': self._get_company,
                    'get_start_period': self.get_start_period,
                    'get_end_period': self.get_end_period,
                    'get_start_date': self._get_start_date,
                    'get_end_date': self._get_end_date,
                    'get_partner_data': self._get_partner_data,
                    'get_line_data': self._get_line_data,
                    'get_total_sale': self._get_total_sale
        })
        self.total_sale =[0.0, '']
        
    def _get_partner_data(self, data):
        customer_list = []
        categ_ids = data['form']['category_ids']
        if categ_ids:
            customers_ids = self.pool.get('res.partner').search(self.cr, self.uid, [('category_id', 'in', categ_ids)])
            customers_data = self.pool.get('res.partner').browse(self.cr, self.uid, customers_ids)
            customer_list.extend(customers_data)
        wiz_customer_ids = data['form']['customer_ids']
        if wiz_customer_ids:
            customers_data = self.pool.get('res.partner').browse(self.cr, self.uid, wiz_customer_ids)
            customer_list.extend(customers_data)
        if not wiz_customer_ids and not categ_ids:
            customers_ids = self.pool.get('res.partner').search(self.cr, self.uid, [])
            customers_data = self.pool.get('res.partner').browse(self.cr, self.uid, customers_ids)
            customer_list.extend(customers_data)
        return customer_list
        
    def _get_line_data(self, partner, data):
        if data['form']['filter'] == 'filter_no':
            self.cr.execute("SELECT \
                                    inv_line.id,  \
                                    tmpl.name as product, \
                                    inv_line.name as description, \
                                    inv_line.quantity as qty, \
                                    uom.name as unit, \
                                    inv_line.price_unit * inv_line.quantity as total_sale, \
                                    invoice.number as invoice_name,\
                                    currency.symbol as symbol\
                                FROM \
                                    account_invoice_line inv_line \
                                LEFT JOIN account_invoice invoice \
                                    ON (inv_line.invoice_id = invoice.id) \
                                LEFT JOIN res_currency currency \
                                    ON (invoice.currency_id = currency.id) \
                                LEFT JOIN product_product product \
                                    ON (inv_line.product_id = product.id) \
                                LEFT JOIN product_template tmpl \
                                    ON (product.product_tmpl_id = tmpl.id) \
                                LEFT JOIN product_uom uom \
                                    ON (tmpl.uom_id = uom.id) \
                                WHERE \
                                    invoice.partner_id = %s and invoice.state not in ('draft', 'cancel') and invoice.type= 'out_invoice' \
                                " %(partner.id))
        else:
            date_start = False
            date_stop = False
            if data['form']['filter'] == 'filter_period':
                start_period_data = self.pool.get('account.period').browse(self.cr, self.uid, data['form']['period_from'])
                date_start = start_period_data.date_start
                end_period_data = self.pool.get('account.period').browse(self.cr, self.uid, data['form']['period_to'])
                date_stop = end_period_data.date_stop
            if data['form']['filter'] == 'filter_date':
                date_start = data['form']['date_from']
                date_stop = data['form']['date_to']
                
            self.cr.execute(""" SELECT 
                                    inv_line.id,
                                    tmpl.name as product,
                                    inv_line.name as description,
                                    inv_line.quantity as qty,
                                    uom.name as unit,
                                    inv_line.price_unit * inv_line.quantity as total_sale,
                                    invoice.number as invoice_name,
                                    currency.symbol as symbol
                                FROM
                                    account_invoice_line inv_line 
                                LEFT JOIN account_invoice invoice
                                    ON (inv_line.invoice_id = invoice.id)
                                LEFT JOIN res_currency currency \
                                    ON (invoice.currency_id = currency.id) \
                                LEFT JOIN product_product product
                                    ON (inv_line.product_id = product.id)
                                LEFT JOIN product_template tmpl
                                    ON (product.product_tmpl_id = tmpl.id)
                                LEFT JOIN product_uom uom
                                    ON (tmpl.uom_id = uom.id)
                                WHERE
                                    invoice.partner_id = %s and invoice.state not in ('draft', 'cancel') and 
                                    invoice.date_invoice <= %s and invoice.date_invoice >= %s and invoice.type= 'out_invoice'
                                """, (partner.id, date_stop, date_start))
        
        query_data = self.cr.dictfetchall()
        self.total_sale = [0.0, '']
        for sale in query_data:
            self.total_sale[0] += sale['total_sale']
            self.total_sale[1] =  sale['symbol']
        return query_data
        
    def _get_total_sale(self):
        return self.total_sale
        
    def _get_start_date(self, data):
        if data.get('form', False) and data['form'].get('date_from', False):
            return data['form']['date_from']
        return ''

    def _get_end_date(self, data):
        if data.get('form', False) and data['form'].get('date_to', False):
            return data['form']['date_to']
        return ''

    def get_start_period(self, data):
        if data.get('form', False) and data['form'].get('period_from', False):
            return self.pool.get('account.period').browse(self.cr, self.uid, data['form']['period_from']).name
        return ''

    def get_end_period(self, data):
        if data.get('form', False) and data['form'].get('period_to', False):
            return self.pool.get('account.period').browse(self.cr, self.uid, data['form']['period_to']).name
        return ''

    def _get_filter(self, data):
        if data.get('form', False) and data['form'].get('filter', False):
            if data['form']['filter'] == 'filter_date':
                return self._translate('Date')
            elif data['form']['filter'] == 'filter_period':
                return self._translate('Periods')
        return self._translate('No Filters')
    
    def _get_company(self, data):
        if data.get('form', False) and data['form'].get('company_id', False):
            return self.pool.get('res.company').browse(self.cr, self.uid, data['form']['company_id'][0]).name
        return ''
    
    def _get_fiscalyear(self, data):
        if data.get('form', False) and data['form'].get('fiscalyear_id', False):
            return self.pool.get('account.fiscalyear').browse(self.cr, self.uid, data['form']['fiscalyear_id']).name
        return ''
    
class report_test(osv.AbstractModel):
    _name = "report.fofo_sales_report.fofo_sales_report"
    _inherit = "report.abstract_report"
    _template = "fofo_sales_report.fofo_sales_report"
    _wrapped_report_class = fofo_sales_detail_report

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
