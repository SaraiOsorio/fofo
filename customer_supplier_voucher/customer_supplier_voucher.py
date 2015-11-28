# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 Kitti
#    Copyright (C) 2010-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp

class account_voucher(models.Model):
    _inherit = 'account.voucher'

    customer_amount = fields.Float(string='Customer Payment', help="Specify the customer payment value. Value specified here will be used in contra entry for payment journal.", digits_compute=dp.get_precision('Account'), required=False, readonly=True, states={'draft':[('readonly', False)]})
    supplier_amount = fields.Float(string='Supplier Payment', help="Specify the supplier payment value. Value specified here will be used in contra entry for payment journal.", digits_compute=dp.get_precision('Account'), required=False, readonly=True, states={'draft':[('readonly', False)]})
    
    @api.multi
    def recompute_voucher_lines(self, partner_id, journal_id, price, currency_id, ttype, date):
        """
        Returns a dict that contains new values and context

        @param partner_id: latest value from user input for field partner_id
        @param args: other arguments
        @param context: context arguments, like lang, time zone

        @return: Returns a dict which contains new values, and context
        """
        def _remove_noise_in_o2m():
            """if the line is partially reconciled, then we must pay attention to display it only once and
                in the good o2m.
                This function returns True if the line is considered as noise and should not be displayed
            """
            if line.reconcile_partial_id:
                if currency_id == line.currency_id.id:
                    if line.amount_residual_currency <= 0:
                        return True
                else:
                    if line.amount_residual <= 0:
                        return True
            return False

        if not self._context.get('mode', False) == 'partner':
            return super(account_voucher, self).recompute_voucher_lines(partner_id, journal_id, price, currency_id, ttype, date)
        
        context_multi_currency = dict(self._context.copy())
        if date:
            context_multi_currency.update({'date': date})

        currency_pool = self.env['res.currency']
        move_line_pool = self.env['account.move.line']
        partner_pool = self.env['res.partner']
        journal_pool = self.env['account.journal']
        line_pool = self.env['account.voucher.line']

        # set default values
        default = {
            'value': {'line_dr_ids': [] , 'line_cr_ids': [] , 'pre_line': False, },
        }

        # drop existing lines
        line_ids = self.ids and line_pool.search([('voucher_id', '=', self.ids[0])])
        #if line_ids:
           # line_ids.unlink()

        for line in line_ids:
            if line.type == 'cr':
                default['value']['line_cr_ids'].append((2, line.id))
            else:
                default['value']['line_dr_ids'].append((2, line.id))

	if not partner_id or not journal_id:
            return default

        journal = journal_pool.browse(journal_id)
        partner = partner_pool.browse(partner_id)
        currency_id = currency_pool.browse(currency_id) or journal.company_id.currency_id
        account_id = False
        if journal.type in ('sale', 'sale_refund'):
            account_id = partner.property_account_receivable.id
        elif journal.type in ('purchase', 'purchase_refund', 'expense'):
            account_id = partner.property_account_payable.id
        else:
            account_id = journal.default_credit_account_id.id or journal.default_debit_account_id.id

        default['value']['account_id'] = account_id

        if journal.type not in ('cash', 'bank'):
            return default

        total_credit = 0.0
        total_debit = 0.0
        account_type = 'receivable'
        if ttype == 'payment':
            account_type = 'payable'
            total_debit = price or 0.0
        else:
            total_credit = price or 0.0
            account_type = 'receivable'

        if not self._context.get('move_line_ids', False):
            ids = move_line_pool.search([('state', '=', 'valid'), ('account_id.type', '=', account_type), ('reconcile_id', '=', False), ('partner_id', '=', partner_id)])
        else:
            ids = self._context['move_line_ids']
        
        if self._context.get('mode', False) == 'partner':
            account_type = ('receivable', 'payable')
            ids = move_line_pool.search([('state', '=', 'valid'), ('account_id.type', 'in', account_type), ('reconcile_id', '=', False), ('partner_id', '=', partner_id)])
        
        invoice_id = self._context.get('invoice_id', False)
        company_currency = journal.company_id.currency_id
        move_line_found = False

        # order the lines by most old first
          #  ids.reverse()
       # account_move_lines = move_line_pool.browse(ids)
        account_move_lines = ids[::-1]
        # compute the total debit/credit and look for a matching open amount or invoice
        for line in account_move_lines:
            if _remove_noise_in_o2m():
                continue

            if invoice_id:
                if line.invoice.id == invoice_id:
                    # if the invoice linked to the voucher line is equal to the invoice_id in context
                    # then we assign the amount on that line, whatever the other voucher lines
                    move_line_found = line.id
                    break
            elif currency_id.id == company_currency.id:
                # otherwise treatments is the same but with other field names
                if line.amount_residual == price:
                    # if the amount residual is equal the amount voucher, we assign it to that voucher
                    # line, whatever the other voucher lines
                    move_line_found = line.id
                    break
                # otherwise we will split the voucher amount on each line (by most old first)
                total_credit += line.credit or 0.0
                total_debit += line.debit or 0.0
            elif currency_id.id == line.currency_id.id:
                if line.amount_residual_currency == price:
                    move_line_found = line.id
                    break
                total_credit += line.credit and line.amount_currency or 0.0
                total_debit += line.debit and line.amount_currency or 0.0

        # voucher line creation
        for line in account_move_lines:

            if _remove_noise_in_o2m():
                continue

            if line.currency_id.id and currency_id.id == line.currency_id.id:
                amount_original = abs(line.amount_currency)
                amount_unreconciled = abs(line.amount_residual_currency)
            else:
               # amount_original = currency_pool.compute(company_currency, currency_id, line.credit or line.debit or 0.0)
                amount_original = company_currency.compute(line.credit or line.debit or 0.0, currency_id)
               # amount_unreconciled = currency_pool.compute(company_currency, currency_id, abs(line.amount_residual))
                amount_unreconciled = company_currency.compute(abs(line.amount_residual), currency_id)
            line_currency_id = line.currency_id and line.currency_id.id or company_currency.id
            rs = {
                'name':line.move_id.name,
                'type': line.credit and 'dr' or 'cr',
                'move_line_id':line.id,
                'account_id':line.account_id.id,
                'amount_original': amount_original,
                'amount': (move_line_found == line.id) and min(abs(price), amount_unreconciled) or 0.0,
                'date_original':line.date,
                'date_due':line.date_maturity,
                'amount_unreconciled': amount_unreconciled,
                'currency_id': line_currency_id,
            }
            # in case a corresponding move_line hasn't been found, we now try to assign the voucher amount
            # on existing invoices: we split voucher amount by most old first, but only for lines in the same currency
            if not move_line_found:
                if currency_id.id == line_currency_id:
                    if line.credit:
                        amount = min(amount_unreconciled, abs(total_debit))
                        rs['amount'] = amount
                        total_debit -= amount
                    else:
                        amount = min(amount_unreconciled, abs(total_credit))
                        rs['amount'] = amount
                        total_credit -= amount

            if rs['amount_unreconciled'] == rs['amount']:
                rs['reconcile'] = True

            if rs['type'] == 'cr':
                default['value']['line_cr_ids'].append(rs)
            else:
                default['value']['line_dr_ids'].append(rs)

            if ttype == 'payment' and len(default['value']['line_cr_ids']) > 0:
                default['value']['pre_line'] = 1
            elif ttype == 'receipt' and len(default['value']['line_dr_ids']) > 0:
                default['value']['pre_line'] = 1
            default['value']['writeoff_amount'] = self._compute_writeoff_amount(default['value']['line_dr_ids'], default['value']['line_cr_ids'], price, ttype)
        return default
    @api.multi
    def action_move_line_create(self):
        '''
        Confirm the vouchers given in ids and create the journal entries for each of them
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
            move_line_brw = move_line_pool.create(self.first_move_line_get(voucher.id, move_id.id, company_currency, current_currency))
            line_total = move_line_brw.debit - move_line_brw.credit
            rec_list_ids = []
            if voucher.type == 'sale':
                line_total = line_total - self.with_context(ctx)._convert_amount(voucher.tax_amount, voucher.id)
            elif voucher.type == 'purchase':
                line_total = line_total + self.with_context(ctx)._convert_amount(voucher.tax_amount, voucher.id)
            # Create one move line per voucher line where amount is not 0.0
            line_total, rec_list_ids = self.voucher_move_line_create(voucher.id, line_total, move_id.id, company_currency, current_currency)

            # Create the writeoff line if needed
            ml_writeoff = voucher.writeoff_move_line_get(line_total, move_id.id, name, company_currency, current_currency)
            if ml_writeoff:
                move_line_pool.create(ml_writeoff)
            # We post the voucher.
            voucher.write({
                'move_id': move_id.id,
                'state': 'posted',
                'number': name,
            })
            if voucher.journal_id.entry_posted:
                move_id.post()
            # We automatically reconcile the account move lines.
            reconcile = False
            for rec_ids in rec_list_ids:
                if len(rec_ids) >= 2:
                    recs = move_line_pool.browse(rec_ids)
                    reconcile = recs.reconcile_partial(writeoff_acc_id=voucher.writeoff_acc_id.id, writeoff_period_id=voucher.period_id.id, writeoff_journal_id=voucher.journal_id.id)
        return True
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
