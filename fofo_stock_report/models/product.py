# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015-Today Ecosoft Co., Ltd. (http://Ecosoft.co.th).
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

class product_product(models.Model):
    _inherit = 'product.product'
    
    @api.one
    @api.depends('orderpoint_ids', 'orderpoint_ids.product_min_qty')
    def _get_reorder_point(self):
        min_qty = 0.0
        if self.orderpoint_ids:
            min_qty = self.orderpoint_ids[0].product_min_qty
        self.reorder_point_report = min_qty
    
    @api.one
    @api.depends('purchase_line_ids','purchase_line_ids.remain_contain_qty','purchase_line_ids.state')
    def _get_po_not_contained_qty(self):
        total_not_contained_qty = 0.0
        if self.purchase_line_ids:
            for purchase in self.purchase_line_ids:
                if purchase.state == 'confirmed':
                    total_not_contained_qty += purchase.remain_contain_qty
        self.po_not_contained_report = total_not_contained_qty
    
    reorder_point_report = fields.Float(compute='_get_reorder_point', string='Reorder Point', store=True)
    po_not_contained_report = fields.Float(compute='_get_po_not_contained_qty', string='PO Not Contained', store=True)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
