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

class import_history(models.Model):
    _name = 'import.history'
    
    name = fields.Char('Import Number')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    seller_sku = fields.Char('Seller SKU', readonly=True)
    created_at = fields.Char('Order Date', readonly=True)
    order_number = fields.Char('Lazada Order Number', readonly=True)
    unit_price = fields.Float('Unit Price', readonly=True)
    status = fields.Char('Lazada Status', readonly=True)
    import_time = fields.Date('Import Date', readonly=True)
    user_id = fields.Many2one('res.users', string= 'Imported By', readonly=True)
    order_status = fields.Selection([('done', 'Succeed'), ('fail', 'Failed')], string='Import Status', readonly=True)
    notes = fields.Text('Failure Reason')
    sale_line_id = fields.Many2one('sale.order.line', string='Sale Order Line')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
