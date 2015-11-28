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

from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, Warning, RedirectWarning

class accuont_voucher_multiple_reconcile(models.Model):
    _name = 'account.voucher.multiple.reconcile'
    _description = 'Account Voucher Multiple Reconcile'
    
    account_id = fields.Many2one('account.account', string='Reconcile Account', required=True)
    amount = fields.Float(string='Amount', digits_compute=dp.get_precision('Account'), required=True)
    comment = fields.Char(string='Comment', required=True)
    voucher_id = fields.Many2one('account.voucher', string='Related Voucher')
    analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    #transaction_type = fields.Char('Transaction Type')
    #order_no = fields.Char('Order Number')

class account_voucher(models.Model):
    _inherit = 'account.voucher'

    @api.multi #Complete override function field from account_voucher module.
    @api.depends('line_cr_ids', 'line_dr_ids', 'multiple_reconcile_ids')
    def _get_writeoff_amount(self):
        if not self.ids:
            return True
        currency_obj = self.env['res.currency']
        res = {}
        for voucher in self:
            debit = 0.0 
            credit =  0.0 
            reconcile_total = 0.0
            if voucher.multiple_reconcile_ids:
                sign = voucher.type == 'payment' and -1 or 1
                for l in voucher.line_dr_ids:
                    debit += l.amount
                for l in voucher.line_cr_ids:
                    credit += l.amount
                if voucher.type == 'receipt':
                    for r in voucher.multiple_reconcile_ids:
                        reconcile_total += r.amount
                elif voucher.type == 'payment':
                    for r in voucher.multiple_reconcile_ids:
                        reconcile_total -= r.amount
                currency = voucher.currency_id or voucher.company_id.currency_id
                voucher.writeoff_amount =  currency.round(voucher.amount - sign * (credit - debit + reconcile_total))
            else:
                sign = voucher.type == 'payment' and -1 or 1
                for l in voucher.line_dr_ids:
                    debit += l.amount
                for l in voucher.line_cr_ids:
                    credit += l.amount
                currency = voucher.currency_id or voucher.company_id.currency_id
                voucher.writeoff_amount =  currency.round(voucher.amount - sign * (credit - debit))

#Columns-------START
    is_lazada_payment = fields.Boolean('Is Lazada Payment?', readonly=True)
    multiple_reconcile_ids = fields.One2many('account.voucher.multiple.reconcile', 'voucher_id', string='Reconcile Liness')
    writeoff_amount = fields.Float(compute=_get_writeoff_amount, string='Difference Amount', readonly=True, help="Computed as the difference between the amount stated in the voucher and the sum of allocation on the voucher lines.")
#Columns----------END

#-------------------------START---------------Logic for creating deduction lines journal entry ----
    @api.model
    def writeoff_move_line_get(self, voucher_id, line_total, move_id, name, company_currency, current_currency):
        move_line = {}
        voucher_brw = self.browse(voucher_id)
        current_currency_obj = voucher_brw.currency_id or voucher_brw.journal_id.company_id.currency_id
        list_move_line = []
        ded_amount = 0.00
        flag = False
        if not current_currency_obj.is_zero(line_total):
            diff = line_total
            account_id = False
            write_off_name = ''
            if voucher_brw.payment_option == 'with_writeoff':
                account_id = voucher_brw.writeoff_acc_id.id
                write_off_name = voucher_brw.comment
            elif voucher_brw.type in ('sale', 'receipt'):
                account_id = voucher_brw.partner_id.property_account_receivable.id
            else:
                account_id = voucher_brw.partner_id.property_account_payable.id
            if voucher_brw.multiple_reconcile_ids:
                if voucher_brw.multiple_reconcile_ids:
                    ctx = dict(self._context.copy())
                    ctx.update({'date': voucher_brw.date})
                    for line in voucher_brw.multiple_reconcile_ids:
                        amount_convert = self.with_context(ctx)._convert_amount(line.amount, voucher_brw.id)  # this will return amount in company currency
                        debit = 0.0
                        credit = 0.0
                        if line.amount < 0.0:
                            if voucher_brw.type == 'receipt':
                                debit = amount_convert #Probuse
                            else:
                                credit = amount_convert #Probuse
                        else:
                            if voucher_brw.type == 'receipt':
                                credit = amount_convert #Probuse
                            else:
                                debit = amount_convert #Probuse
                        
                        debit = voucher_brw.company_id.currency_id.round((debit))
                        credit = voucher_brw.company_id.currency_id.round((credit))
                        if abs(debit) > 0.0:
                            sign = 1
                        else:
                            sign = -1
                        move_line = {
                            'name': line.comment or name,
                            'account_id': line.account_id.id,
                            'move_id': move_id,
                            'partner_id': voucher_brw.partner_id.id,
                            'date': voucher_brw.date,
                            'credit': abs(credit),  # abs(credit[0]),
                            'debit': abs(debit),  # abs(debit[0]),
                            'amount_currency': company_currency <> current_currency and sign * abs(line.amount) or 0.0,
                            'currency_id': company_currency <> current_currency and current_currency or False,
                            'analytic_account_id': line.analytic_id and line.analytic_id.id or False,
                        }
                        ded_amount += voucher_brw.company_id.currency_id.round((amount_convert))  # today
                        list_move_line.append(move_line)
            if not voucher_brw.multiple_reconcile_ids:
                sign = voucher_brw.type == 'payment' and -1 or 1
                move_line = {
                    'name': write_off_name or name,
                    'account_id': account_id,
                    'move_id': move_id,
                    'partner_id': voucher_brw.partner_id.id,
                    'date': voucher_brw.date,
                    'credit': diff > 0 and diff or 0.0,
                    'debit': diff < 0 and -diff or 0.0,
                    'amount_currency': company_currency <> current_currency and (sign * -1 * voucher_brw.writeoff_amount) or False,
                    'currency_id': company_currency <> current_currency and current_currency or False,
                    #'analytic_account_id': voucher_brw.analytic_id and voucher_brw.analytic_id.id or False,
                }
                list_move_line.append(move_line)
            elif voucher_brw.multiple_reconcile_ids and diff != ded_amount:
                value1 = self.with_context(ctx)._convert_amount(voucher_brw.writeoff_amount, voucher_brw.id)  # this will return amount in company currency
                if value1 != 0.0:
                    if value1 < 0.0:
                        if voucher_brw.type == 'receipt':
                            debit = value1 #Probuse
                        else:
                            credit = value1 #Probuse
                    else:
                        if voucher_brw.type == 'receipt':
                            credit = value1 #Probuse
                        else:
                            debit = value1 #Probuse

                    sign = voucher_brw.type == 'payment' and -1 or 1
                    move_line = {
                        'name': write_off_name or name,
                        'account_id': account_id,
                        'move_id': move_id,
                        'partner_id': voucher_brw.partner_id.id,
                        'date': voucher_brw.date,
                        'credit': abs(credit),
                        'debit': abs(debit),
                        'amount_currency': company_currency <> current_currency and (sign * -1 * voucher_brw.writeoff_amount) or False,
                        'currency_id': company_currency <> current_currency and current_currency or False,
                        #'analytic_account_id': voucher_brw.analytic_id and voucher_brw.analytic_id.id or False,
                    }
                    list_move_line.append(move_line)
            return list_move_line

    #Below method is completly override from account_voucher module.    
    @api.multi
    def action_move_line_create(self):
        '''
        See probuse tag for changes by Probuse.
        '''
        move_pool = self.env['account.move']
        move_line_pool = self.env['account.move.line']
        for voucher in self:
            if voucher.move_id:
                continue
            company_currency = self._get_company_currency(voucher.id)
            current_currency = self._get_current_currency(voucher.id)
            # we select the context to use accordingly if it's a multicurrency case or not
            context = self._sel_context(voucher.id)
            # But for the operations made by _convert_amount, we always need to give the date in the context
            ctx = context.copy()
            ctx.update({'date': voucher.date})
            # Create the account move record.
            move_id = move_pool.create(self.account_move_get(voucher.id))
            # Get the name of the account_move just created
            name = move_id.name
            # Create the first line of the voucher
            move_line_id = move_line_pool.create(self.first_move_line_get(voucher.id, move_id.id, company_currency, current_currency))
            move_line_brw = move_line_id
            line_total = move_line_brw.debit - move_line_brw.credit
            rec_list_ids = []
            if voucher.type == 'sale':
                line_total = line_total - voucher.with_context(ctx)._convert_amount(voucher.tax_amount, voucher.id)
            elif voucher.type == 'purchase':
                line_total = line_total + self.with_context(ctx)._convert_amount(voucher.tax_amount, voucher.id)

            # Create one move line per voucher line where amount is not 0.0
            line_total, rec_list_ids = self.voucher_move_line_create(voucher.id, line_total, move_id.id, company_currency, current_currency)

            # Create the writeoff line if needed
            ml_writeoff = voucher.writeoff_move_line_get(voucher.id, line_total, move_id.id, name, company_currency, current_currency)
            
            #PROBUSE CHANGE STARTED Section 1 ----------------------
            if voucher.multiple_reconcile_ids:
                if ml_writeoff:
                    for line_tax in ml_writeoff:
                        writeoff_id = move_line_pool.create(line_tax)
            else:
                if ml_writeoff: #Odoo standard
                    move_line_pool.create(ml_writeoff[0]) #Odoo standard
            #PROBUSE CHANGE END Section 1----------------------

            # We post the voucher.
            voucher.write({
                'move_id': move_id.id,
                'state': 'posted',
                'number': name,
            })

            if voucher.journal_id.entry_posted:
                move_id.post()
            # We automatically reconcile the account move lines.
            for rec_ids in rec_list_ids:
                if len(rec_ids) >= 2:
                    recs = move_line_pool.browse(rec_ids)
                    #reconcile = move_line_pool.reconcile_partial(cr, uid, rec_ids, writeoff_acc_id=voucher.writeoff_acc_id.id, writeoff_period_id=voucher.period_id.id, writeoff_journal_id=voucher.journal_id.id) #This is Standard odoo code.
                    if voucher.writeoff_amount == 0.0 and not voucher.multiple_reconcile_ids:
                        recs.reconcile_partial(type='manual')#Probuse
                    elif voucher.writeoff_amount == 0.0 and voucher.multiple_reconcile_ids:
                        recs.reconcile_partial(type='manual')#Probuse
                    elif voucher.writeoff_amount == 0.0 or voucher.multiple_reconcile_ids:#Probuse
                        recs.reconcile(type='manual')#Probuse
                    else:#Probuse
                        recs.reconcile_partial(type='manual')#Probuse
        return True
#------------------------END--------------------------------------------------------------

    @api.multi
    def button_reset_amount(self):
        return self.write({'multiple_reconcile_ids': []})


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
