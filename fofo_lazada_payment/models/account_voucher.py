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
    
    account_id = fields.Many2one('account.account', string='Reconcile Account', required=False)
    amount = fields.Float(string='Amount', digits_compute=dp.get_precision('Account'), required=False)
    comment = fields.Char(string='Comment', required=False)
    voucher_id = fields.Many2one('account.voucher', string='Related Voucher')
    analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    transaction_type = fields.Char('Transaction Type')
    order_no = fields.Char('Order Number')

class account_voucher(models.Model):
    _inherit = 'account.voucher'
    
    @api.multi
    @api.depends('line_cr_ids', 'line_dr_ids', 'multiple_reconcile_ids')
    def _get_writeoff_amount(self):
        if not self.ids: return {}
        currency_obj = self.env['res.currency']
        res = {}
        debit = credit = reconcile_total = 0.0
        for voucher in self:
            if voucher.reconcile_payment:
                sign = voucher.type == 'payment' and -1 or 1
                for l in voucher.line_dr_ids:
                    debit += l.amount
                for l in voucher.line_cr_ids:
                    credit += l.amount
                for r in voucher.multiple_reconcile_ids:
                    reconcile_total += r.amount
                currency = voucher.currency_id or voucher.company_id.currency_id
                self.writeoff_amount =  currency.round(voucher.amount - sign * (credit - debit + reconcile_total))
            else:
                return super(account_voucher, self)._get_writeoff_amount()
                
    reconcile_payment = fields.Boolean('Reconcile Payment', default=False)
    is_lazada_payment = fields.Boolean('Is Lazada Payment?', readonly=True)
    multiple_reconcile_ids = fields.One2many('account.voucher.multiple.reconcile', 'voucher_id', string='Reconcile Liness')
    writeoff_amount = fields.Float(compute=_get_writeoff_amount, string='Difference Amount', readonly=True, help="Computed as the difference between the amount stated in the voucher and the sum of allocation on the voucher lines.")
#     
    @api.multi
    def write(self, vals):
        if self.is_lazada_payment:
            if vals.get('multiple_reconcile_ids', False) or vals.get('journal_id') or vals.get('line_cr_ids') or vals.get('line_dr_ids') or vals.get('date') or vals.get('period_id'): 
                raise Warning(_('Warning!'),_('You can not modify values of some columns on lazada customer payment which has been created by wizard.'))
        return super(account_voucher, self).write(vals)
    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
