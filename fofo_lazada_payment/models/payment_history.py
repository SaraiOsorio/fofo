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

class payment_history_line(models.Model):
    _name = 'payment.history.line'

    date = fields.Date('Date')
    transaction_type = fields.Char('Transaction Type')
    transaction_number = fields.Char('Transaction Number')
    amount = fields.Float('Amount')
    amount_vat = fields.Float('Amount VAT')
    ref = fields.Char('Reference')
    seller_sku = fields.Char('Seller SKU')
    lazada_sku = fields.Char('Lazada SKU')
    order_no = fields.Char('Order No')
    order_item_no = fields.Char('Order Item No')
    history_id = fields.Many2one('payment.history', string="History", ondelete='cascade')
    status = fields.Selection([('Fail', 'Failed'), ('Done', 'Succeed')], string='Status')
    details = fields.Text('Detail')
    
    

class payment_history(models.Model):
    _name = 'payment.history'
    
    name = fields.Char('History Number')
    partner_id = fields.Many2one('res.partner', string='Partner')
    journal_id = fields.Many2one('account.journal', string='Journal')
    currency_id = fields.Many2one('res.currency', string='Currency')
    import_date = fields.Date('Import Date')
    history_line_ids = fields.One2many('payment.history.line', 'history_id', string='History Lines')
    bill_id = fields.Many2one('account.billing', string="Bill")
    voucher_id = fields.Many2one('account.voucher', string="Voucher")


    @api.model
    def create(self, vals):
        if vals.get('name') == '/' or False:
            vals['name'] = self.env['ir.sequence'].get('lazada.payment.history')
        return super(payment_history, self).create(vals)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: