# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015-Today Ecosoft Co., Ltd. (http://ecosoft.co.th).
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

import xlrd
import csv
import StringIO
import base64
import time
from datetime import date

from openerp import models, fields, api, _


class account_billing_line(models.Model):
    _inherit = 'account.billing.line'
    
    @api.one
    @api.depends('move_line_id', 'move_line_id.invoice')
    def _get_so_reference(self):
        invoice_id = self.move_line_id.invoice
        if invoice_id.origin:
            self.sale_order = invoice_id.origin
    
    sale_order = fields.Char(compute=_get_so_reference,string='#SO')


class lazada_payment(models.TransientModel):
    _name = 'lazada.payment'
    
    @api.multi
    def _get_partner(self):
        partner = self.env['ir.model.data'].get_object_reference('fofo_lazada', 'res_partner_lazada')[1]
        return partner or False
    
    input_file = fields.Binary('Lazada Payment File (.xlsx format)')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id.id)
    date = fields.Date('Date', required=True, default= fields.Date.today())
    partner_id = fields.Many2one('res.partner', string='Customer',default=_get_partner, readonly=True)

    @api.multi
    def import_payment(self):
        history_line_vals= {}
        partner = self.partner_id.id
        company = self.journal_id.company_id.id
        journal = self.journal_id.id
        currency = self.currency_id.id
        bill_date = self.date

        bill_vals = {
            'partner_id' : partner,
            'company_id' : company,
            'journal_id' : journal,
            'currency_id': currency,
            'line_ids' : False,
            'line_cr_ids' : False
        }
        bill_id = self.env['account.billing'].create(bill_vals)
        partner_data = self.env['account.billing'].onchange_partner_id(partner, journal, 0.0, currency, bill_date)
        histoy_vals = {'partner_id' : partner,
                    'currency_id' : currency,
                    'journal_id' : journal,
                    'history_line_ids' : False,
                    'bill_id': bill_id.id,
                    'import_date' : date.today().strftime("%m/%d/%Y")}
        history_id = self.env['payment.history'].create(histoy_vals)
        
        order_journal_dict = {}
        for line in self:
            lines = xlrd.open_workbook(file_contents=base64.decodestring(self.input_file))
            for sheet_name in lines.sheet_names(): 
                sheet = lines.sheet_by_name(sheet_name)
                rows = sheet.nrows
                columns = sheet.ncols
                amount_row = sheet.row_values(0).index('Amount')
                for row_no in range(rows):
                    order_row = sheet.row_values(0).index('Order No')
                    order_no = False
                    try:
                        order_no = int(sheet.row_values(row_no)[order_row])
                    except:
                        order_no = False
                    if order_no:
                        if row_no > 0:
                            amount = sheet.row_values(row_no)[amount_row]
                            sheet_date = sheet.row_values(row_no)[sheet.row_values(0).index('Date')]
                            conv_date = time.strptime(sheet_date,"%d %b %Y")
                            billing_date = time.strftime("%m/%d/%Y",conv_date)
                            transaction_type = sheet.row_values(row_no)[sheet.row_values(0).index('Transaction Type')]
                            transaction_number = sheet.row_values(row_no)[sheet.row_values(0).index('Transaction Number')]
                            amount_vat = sheet.row_values(row_no)[sheet.row_values(0).index('VAT in Amount')]
                            ref = int(sheet.row_values(row_no)[sheet.row_values(0).index('Reference')])
                            seller_sku = sheet.row_values(row_no)[sheet.row_values(0).index('Seller SKU')]
                            lazada_sku = sheet.row_values(row_no)[sheet.row_values(0).index('Lazada SKU')]
                            details = sheet.row_values(row_no)[sheet.row_values(0).index('Details')]
                            order_item_no = int(sheet.row_values(row_no)[sheet.row_values(0).index('Order Item No')])
                            history_line_vals.update({
                                'date': billing_date,
                                'transaction_type': transaction_type,
                                'transaction_number': transaction_number,
                                'amount': amount,
                                'amount_vat': amount_vat,
                                'ref': ref,
                                'seller_sku' : seller_sku,
                                'lazada_sku': lazada_sku,
                                'order_no': str(sheet.row_values(row_no)[order_row]).split('.')[0],
                                'order_item_no' : order_item_no,
                                'history_id' : history_id.id,
                                'status' : 'Done',
                                'details': details
                            })
                            if not amount < 0:
                                move_ids = self.env['account.move.line'].search([('lazada_order_no' ,'=', order_no), ('debit', '>', 0.0)])
                                if move_ids:
                                    if not order_no in order_journal_dict:
                                        order_journal_dict[order_no] = (move_ids.id, amount)
                                    else:
                                        amount += amount
                                        order_journal_dict[order_no] = (move_ids.id, amount)
                    else:
                        history_line_vals.update({'status' : 'Fail', 'order_no': False})
                    history_lines = self.env['payment.history.line'].create(history_line_vals)
            
        for order in order_journal_dict:
            moveline_id = order_journal_dict[order][0]
            move_amount = order_journal_dict[order][1]
            for line in partner_data['value']['line_cr_ids']:
                if line['move_line_id'] == moveline_id:
                    line['amount'] = move_amount
                    bill_id.write({'line_cr_ids' : [(0, 0, line)]})
                    
        result = self.env.ref('fofo_lazada_payment.lazada_payment_import_history_action')
        result = result.read()[0]
        result['domain'] = str([('id','in',[history_id.id])])
        return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: