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
import sys
import time
from datetime import date
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import models, fields, api, _

class account_voucher_line(models.Model):
    _inherit = 'account.voucher.line'
     
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
    
    input_file = fields.Binary('Select Lazada Payment File')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, help='This journal will be used as customer payment journal.')
    account_id = fields.Many2one('account.account', string='Account', required=False)
    currency_id = fields.Many2one('res.currency', string='Currency', required=False, default=lambda self: self.env.user.company_id.currency_id.id)
    date = fields.Date('Date', required=True, default= fields.Date.today(), help='This date will be used as customer payment date.')
    partner_id = fields.Many2one('res.partner', string='Customer',default=_get_partner, readonly=True)

    @api.multi
    def import_payment(self):
        history_line_vals= {}
        partner = self.partner_id.id
        company = self.journal_id.company_id.id
        journal = self.journal_id.id
        bill_date = self.date
        local_context = self.env.context.copy()
        local_context.update({'date': self.date, 'company_id': self.journal_id.company_id.id})
        journal_data = self.env['account.voucher'].with_context(local_context).onchange_journal_voucher(line_ids= False, tax_id=False, price=0.0, partner_id=partner, journal_id=journal, ttype=False, company_id=False)
        period_ids = self.env['account.period'].with_context(local_context).find(dt=self.date)
        if not period_ids:
            raise Warning(_('Import Error!'),_('No period found for given date.'))
        currency = journal_data['value']['currency_id']
        voucher_vals = {
            'name': '/',
            'partner_id' : partner,
            'company_id' : company,
            'journal_id' : journal,
            'currency_id': currency,
            'line_ids' : False,
            'line_cr_ids' : False,
            'account_id' : journal_data['value']['account_id'],
            'period_id': period_ids.id,
            'state': 'draft',
            'date' : bill_date,
            'type': journal_data['value']['type'],
        }
        partner_data = self.env['account.voucher'].onchange_partner_id(partner, journal, 0.0, currency, False ,bill_date)
        histoy_vals = {'name':'/',
                       'partner_id' : partner,
                    'currency_id' : currency,
                    'journal_id' : journal,
                    'history_line_ids' : False,
                    'voucher_id': False,
                    'status': 'Done',
                    'input_file': self.input_file,
                    'user_id': self.env.user.id,
                    'import_date' : date.today().strftime("%m/%d/%Y")}
        history_id = self.env['payment.history'].create(histoy_vals)
        multiple_reconcile_dict = {}
        order_list = []
        cr_move_ids = []
        dr_move_ids = []
        total_amount = 0.0
        STATE_TO_SKIP = []
        state_to_skip_ids = self.env['lazada.payment.transaction.config'].search([('state_to_skip', '=', True)])
        for state in state_to_skip_ids:
            STATE_TO_SKIP.append(state.transaction_type_name)
        
        for line in self:
            try:
                lines = xlrd.open_workbook(file_contents=base64.decodestring(self.input_file))
            except IOError as e:
                raise Warning(_('Import Error!'),_(e.strerror))
            except ValueError as e:
                raise Warning(_('Import Error!'),_(e.strerror))
            except:
                e = sys.exc_info()[0]
                raise Warning(_('Import Error!'),_('Wrong file format. Please enter .xlsx file.'))
            
            for sheet_name in lines.sheet_names(): 
                sheet = lines.sheet_by_name(sheet_name)
                rows = sheet.nrows
                columns = sheet.ncols
                amount_row = sheet.row_values(0).index('Amount')
                odoo_order_exception = False
                reason = 'Error in Order Numbers: '
                order_no_reason = []
                len_rows = rows - 1
                len_rows_counter = 0
                for row_no in range(rows):
                    order_row = sheet.row_values(0).index('Order No.')
                    order_no = False
                    try:
                        order_no = int(sheet.row_values(row_no)[order_row])
                    except:
                        order_no = False
                    if row_no > 0:
                        transaction_type = sheet.row_values(row_no)[sheet.row_values(0).index('Transaction Type')]
                        order_list.append({'order_no': order_no, 'transaction_type': transaction_type})
                        if order_no or transaction_type in STATE_TO_SKIP:
                            line_move_ids = self.env['account.move.line'].search([('lazada_order_no' ,'=', order_no), ('debit', '>', 0.0)])
                            if not line_move_ids:#If order number exists in excel but is not available in Odoo then we will fail that import and not create any customer payment.
                                len_rows_counter += 1
                                odoo_order_exception = True
                                amount = sheet.row_values(row_no)[amount_row]
                                sheet_date = sheet.row_values(row_no)[sheet.row_values(0).index('Transaction Date')]
                                if sheet_date:
                                    conv_date = time.strptime(sheet_date,"%d %b %Y")
                                    billing_date = time.strftime("%m/%d/%Y",conv_date)
                                else:
                                    conv_date = False
                                    billing_date = False
                                
                                transaction_number = sheet.row_values(row_no)[sheet.row_values(0).index('Transaction Number')]
                                amount_vat = sheet.row_values(row_no)[sheet.row_values(0).index('VAT in Amount')]
                                ref = sheet.row_values(row_no)[sheet.row_values(0).index('Reference')]
                                seller_sku = sheet.row_values(row_no)[sheet.row_values(0).index('Seller SKU')]
                                lazada_sku = sheet.row_values(row_no)[sheet.row_values(0).index('Lazada SKU')]
                                details = sheet.row_values(row_no)[sheet.row_values(0).index('Details')]


                                try: #3590
                                   order_item_no = int(sheet.row_values(row_no)[sheet.row_values(0).index('Order Item No')])
                               except:
                                   order_item_no = sheet.row_values(row_no)[sheet.row_values(0).index('Order Item No')]

#                                order_item_no = sheet.row_values(row_no)[sheet.row_values(0).index('Order Item No.')]
                                history_line_vals.update({
                                    'date': billing_date,
                                    'transaction_type': transaction_type,
                                    'transaction_number': transaction_number,
                                    'amount': amount,
                                    'amount_vat': amount_vat,
                                    'ref': ref,
                                    'seller_sku' : seller_sku,
                                    'lazada_sku': lazada_sku,
                                    'order_no': False,
                                    'order_item_no' : order_item_no,
                                    'history_id' : history_id.id,
                                    'status' : 'Fail',
                                    'details': details
                                })
                                history_id.status = 'Fail'
                                if order_no not in order_no_reason:
                                    order_no_reason.append(order_no)
                                    reason = reason + '  ' + str(order_no)
                                    history_id.reason = reason
                            else:
                                amount = sheet.row_values(row_no)[amount_row]
                                sheet_date = sheet.row_values(row_no)[sheet.row_values(0).index('Transaction Date')]
                                conv_date = time.strptime(sheet_date,"%d %b %Y")
                                billing_date = time.strftime("%m/%d/%Y",conv_date)
                                transaction_type = sheet.row_values(row_no)[sheet.row_values(0).index('Transaction Type')]
                                transaction_number = sheet.row_values(row_no)[sheet.row_values(0).index('Transaction Number')]
                                amount_vat = sheet.row_values(row_no)[sheet.row_values(0).index('VAT in Amount')]
                                ref = int(sheet.row_values(row_no)[sheet.row_values(0).index('Reference')])
                                seller_sku = sheet.row_values(row_no)[sheet.row_values(0).index('Seller SKU')]
                                lazada_sku = sheet.row_values(row_no)[sheet.row_values(0).index('Lazada SKU')]
                                details = sheet.row_values(row_no)[sheet.row_values(0).index('Details')]
                                try: #3590
                                   order_item_no = int(sheet.row_values(row_no)[sheet.row_values(0).index('Order Item No')])
                               except:
                                   order_item_no = sheet.row_values(row_no)[sheet.row_values(0).index('Order Item No')]

#                                order_item_no = int(sheet.row_values(row_no)[sheet.row_values(0).index('Order Item No.')])
                                if not transaction_type == "Item Price":
                                    total_amount += float(amount)
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
                                if not amount < 0 and transaction_type == "Item Price Credit" or transaction_type == "Item Price":
                                    move_ids = self.env['account.move.line'].search([('lazada_order_no' ,'=', order_no), ('debit', '>', 0.0)])
                                    if move_ids:
                                        for move in move_ids:
                                            if not move.id in cr_move_ids:
                                                cr_move_ids.append(move.id)
                                    if partner_data['value'].get('line_dr_ids'):
                                        move_dr_ids = self.env['account.move.line'].search([('lazada_order_no' ,'=', order_no), ('credit', '>', 0.0)])
                                        if move_dr_ids:
                                            for move_dr in move_dr_ids:
                                                if not move_dr.id in dr_move_ids:
                                                    dr_move_ids.append(move_dr.id)
                                    
                                elif not transaction_type == "Item Price Credit" or not transaction_type == "Item Price":
                                    transaction_id = self.env['lazada.payment.transaction.type'].search([('name', '=', str(transaction_type))])
                                    if not transaction_id:
                                        raise Warning(_('Please create transaction type for %s') %str(transaction_type) )
                                    transaction_type_id = self.env['lazada.payment.transaction.config'].search([('transaction_type_name', '=', str(transaction_type))])
                                    if not transaction_type_id.account_id:
                                        raise Warning(_('Please configure all transaction type configuration and set accounts related to all transaction types.'))
                                    if not order_no in multiple_reconcile_dict:
                                        multiple_reconcile_dict[order_no] = [{'transaction_type': transaction_type,
                                                                             'amount': amount,
                                                                             'account_id' : transaction_type_id.account_id.id, 
                                                                             'order_no' : order_no}]
                                    else:
                                        multiple_reconcile_dict[order_no].append({'transaction_type': transaction_type,
                                                                                  'amount': amount,
                                                                                  'account_id' : transaction_type_id.account_id.id,
                                                                                  'order_no' : order_no})
                        else:
                            amount = sheet.row_values(row_no)[amount_row]
                            sheet_date = sheet.row_values(row_no)[sheet.row_values(0).index('Transaction Date')]
                            if sheet_date:
                                conv_date = time.strptime(sheet_date,"%d %b %Y")
                                billing_date = time.strftime("%m/%d/%Y",conv_date)
                            else:
                                conv_date = False
                                billing_date = False
                            transaction_type = sheet.row_values(row_no)[sheet.row_values(0).index('Transaction Type')]
                            transaction_number = sheet.row_values(row_no)[sheet.row_values(0).index('Transaction Number')]
                            amount_vat = sheet.row_values(row_no)[sheet.row_values(0).index('VAT in Amount')]
                            ref = sheet.row_values(row_no)[sheet.row_values(0).index('Reference')]
                            seller_sku = sheet.row_values(row_no)[sheet.row_values(0).index('Seller SKU')]
                            lazada_sku = sheet.row_values(row_no)[sheet.row_values(0).index('Lazada SKU')]
                            details = sheet.row_values(row_no)[sheet.row_values(0).index('Details')]
                            order_item_no = sheet.row_values(row_no)[sheet.row_values(0).index('Order Item No.')]
                            history_line_vals.update({
                                'date': billing_date,
                                'transaction_type': transaction_type,
                                'transaction_number': transaction_number,
                                'amount': amount,
                                'amount_vat': amount_vat,
                                'ref': ref,
                                'seller_sku' : seller_sku,
                                'lazada_sku': lazada_sku,
                                'order_no': False,
                                'order_item_no' : order_item_no,
                                'history_id' : history_id.id,
                                'status' : 'Fail',
                                'details': details
                            })
                            history_id.status = 'Fail'
                            reason = reason + '  ' + 'Empty Order Number in sheet  '
                            history_id.reason = reason
                    history_lines = self.env['payment.history.line'].create(history_line_vals)
                break  # 1 sheet only
        

        order_exception = False
        for order in order_list:#This is loop for missing order number in excel file. Column of order number in excel is empty then we will not create any customer payment.
            if not order['order_no'] and order['transaction_type'] not in STATE_TO_SKIP:
                order_exception = True

        if len_rows_counter >= len_rows:
            raise Warning(_('Import Error!'),_('Invoice balance mismatch. No Payment can be created. Please check if you are reimporting old sheet again.')) # this is the reimport case when user try to reimport file which already imported before and already validated.
        
        if not order_exception and not odoo_order_exception:
            voucher_id = self.env['account.voucher'].create(voucher_vals)
            history_id.voucher_id = voucher_id.id
            
            
            for order in multiple_reconcile_dict:
                for line in multiple_reconcile_dict[order]:
                    reconcile_vals = {
                        'account_id': line['account_id'],
                        'amount' : line['amount'],
                        'comment' : line['transaction_type'],
                        'voucher_id': voucher_id.id,
                        'order_no': line['order_no']
                    }
                    self.env['account.voucher.multiple.reconcile'].create(reconcile_vals)
                    
            for move in cr_move_ids:
                for line in partner_data['value']['line_cr_ids']:
                    if line['move_line_id'] == move:
                        line['amount'] = line['amount_original']
                        voucher_id.write({'line_cr_ids' : [(0, 0, line)]})
            
            if partner_data['value'].get('line_dr_ids'):
                for move in dr_move_ids:
                    for line in partner_data['value']['line_dr_ids']:
                        if line['move_line_id'] == move:
                            voucher_id.write({'pre_line': True,'line_dr_ids' : [(0, 0, line)]})
                            total_amount -= line['amount']
            voucher_id.write({'is_lazada_payment' : True, 'amount' : total_amount})
        result = self.env.ref('fofo_lazada_payment.lazada_payment_import_history_action')
        result = result.read()[0]
        result['domain'] = str([('id','in',[history_id.id])])
        return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
