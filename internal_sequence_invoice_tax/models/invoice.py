# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 Ecosoft Co., Ltd. (http://ecosoft.co.th).
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

from openerp import fields, models, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning

class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    is_tax_invoice_number = fields.Boolean('Run Tax Invoice Number', help='If this checkbox is ticked system will generate tax invoice number along with normal sequence number of invoice document.', defatul=False, readonly=True, states={'draft': [('readonly', False)]})
    tax_invoice_number = fields.Char('Tax Invoice Number', readonly=True, states={'draft': [('readonly', False)]}, copy=False)
        
    @api.multi
    def action_number(self):
        res = super(account_invoice, self).action_number()
        for inv in self:
            if inv.is_tax_invoice_number and not inv.tax_invoice_number:
                seq_tax = self.env['ir.sequence'].get('account.invoice.internal') or '/'
                inv.tax_invoice_number = seq_tax
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
    
