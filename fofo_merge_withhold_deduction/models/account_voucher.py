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


class account_voucher(models.Model):
    _inherit = 'account.voucher'

    @api.multi #Complete override function field from account_voucher module. _get_writeoff_amount method here will be override here from account_voucher_deduction and account_undue_withhold_tax. That means _get_writeoff_amount method combincation of both modules logic.
    @api.depends('line_cr_ids', 'line_dr_ids', 'multiple_reconcile_ids')
    def _get_writeoff_amount(self):
        if not self.ids:
            return True
        currency_obj = self.env['res.currency']
        res = {}
        for voucher in self:
            debit = 0.0
            credit = 0.0
            reconcile_total = 0.0
            if voucher.multiple_reconcile_ids:
                sign = voucher.type == 'payment' and -1 or 1
                for l in voucher.line_dr_ids:
                    # ECOSOFT added WHT/Retention
                    # debit += l.amount
                    debit += l.amount + l.amount_wht + l.amount_retention
                    # --
                for l in voucher.line_cr_ids:
                    # ECOSOFT
                    # credit += l.amount
                    credit += l.amount + l.amount_wht + l.amount_retention
                    # --

                #Probuse  ----- START
                if voucher.type == 'receipt':
                    for r in voucher.multiple_reconcile_ids:
                        reconcile_total += r.amount
                elif voucher.type == 'payment':
                    for r in voucher.multiple_reconcile_ids:
                        reconcile_total -= r.amount
                #Probuse  -----END

                currency = voucher.currency_id or voucher.company_id.currency_id
                #self.writeoff_amount =  currency.round(voucher.amount - sign * (credit - debit)) -- STANDARD CODE
                voucher.writeoff_amount = currency.round(voucher.amount - sign * (credit - debit + reconcile_total)) #Probuse
            else:
                sign = voucher.type == 'payment' and -1 or 1
                for l in voucher.line_dr_ids:
                    # ECOSOFT added WHT/Retention
                    # debit += l.amount
                    debit += l.amount + l.amount_wht + l.amount_retention
                    # --
                for l in voucher.line_cr_ids:
                    # ECOSOFT
                    # credit += l.amount
                    credit += l.amount + l.amount_wht + l.amount_retention
                    # --
                currency = voucher.currency_id or voucher.company_id.currency_id
                voucher.writeoff_amount = currency.round(voucher.amount - sign * (credit - debit))

    writeoff_amount = fields.Float(compute=_get_writeoff_amount, string='Difference Amount', readonly=True, help="Computed as the difference between the amount stated in the voucher and the sum of allocation on the voucher lines.")

    # Below method is completly override from account_voucher module.    
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
            # ECOSOFT
            net_tax = 0.0
            net_retention = 0.0
            # --
            if voucher.type == 'sale':
                line_total = line_total - voucher.with_context(ctx)._convert_amount(voucher.tax_amount, voucher.id)
            elif voucher.type == 'purchase':
                line_total = line_total + self.with_context(ctx)._convert_amount(voucher.tax_amount, voucher.id)
            # ECOSOFT
            elif voucher.type in ('receipt', 'payment'):
                net_tax = voucher.voucher_move_line_tax_create(
                    voucher,
                    move_id.id, company_currency,
                    current_currency)
                net_retention = voucher.voucher_move_line_retention_create(
                    voucher,
                    move_id.id, company_currency,
                    current_currency)
            # --
            # Create one move line per voucher line where amount is not 0.0
            line_total, rec_list_ids = self.voucher_move_line_create(voucher.id, line_total, move_id.id, company_currency, current_currency)
            # ECOSOFT - Thai Accounting, adjust with tax before writeoff.
            line_total = line_total + net_tax + net_retention
            # --
            # Create the writeoff line if needed
            ml_writeoff = voucher.writeoff_move_line_get(line_total, move_id.id, name, company_currency, current_currency)
            
            #PROBUSE CHANGE STARTED  ----------------------
            if voucher.multiple_reconcile_ids:
                if ml_writeoff:
                    for line_tax in ml_writeoff:
                        writeoff_id = move_line_pool.create(line_tax)
            else:
                if ml_writeoff: #Odoo standard
                    move_line_pool.create(ml_writeoff[0]) #Odoo standard
            #PROBUSE CHANGE END ----------------------------

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
                    #reconcile = move_line_pool.reconcile_partial(cr, uid, rec_ids, writeoff_acc_id=voucher.writeoff_acc_id.id, writeoff_period_id=voucher.period_id.id, writeoff_journal_id=voucher.journal_id.id) #Odoo standard
                    if voucher.writeoff_amount == 0.0 and not voucher.multiple_reconcile_ids:#Probuse
                        recs.reconcile_partial(type='manual')#Probuse
                    elif voucher.writeoff_amount == 0.0 and voucher.multiple_reconcile_ids:#Probuse
                        recs.reconcile_partial(type='manual')#Probuse
                    elif voucher.writeoff_amount == 0.0 or voucher.multiple_reconcile_ids:#Probuse
                        recs.reconcile(type='manual')#Probuse
                    else:#Probuse
                        recs.reconcile_partial(type='manual')#Probuse
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
