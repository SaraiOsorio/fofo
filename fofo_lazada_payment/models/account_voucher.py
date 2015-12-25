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
    _inherit = 'account.voucher.multiple.reconcile'
    
    transaction_type = fields.Char('Transaction Type')
    order_no = fields.Char('Order Number')

class account_voucher(models.Model):
    _inherit = 'account.voucher'

    @api.multi
    def write(self, vals):
        if self.is_lazada_payment:
            if vals.get('multiple_reconcile_ids', False) or vals.get('journal_id') or vals.get('line_cr_ids') or vals.get('line_dr_ids') or vals.get('date') or vals.get('period_id') or vals.get('amount'): 
                raise Warning(_('Warning!'),_('You can not modify values of some columns on lazada customer payment which has been created by lazada wizard.'))
        return super(account_voucher, self).write(vals)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
