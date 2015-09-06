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
import openerp.addons.decimal_precision as dp

class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    container_id = fields.Many2one('container.order', string="Related Container Order")
    is_shipper_invoice = fields.Boolean('Shipper Invoice', help='If this check box is ticked that will indicate the invoice is related to shipper.')

    @api.multi
    def action_move_create(self):
        res = super(account_invoice, self).action_move_create()
        for inv in self:
            if inv.container_id:
                if inv.is_shipper_invoice:
                    ship_cost_by_volume = inv.amount_total / inv.container_id.total_volume #do computation here same like function field on shiping_cost_by_volumne on CO object.
                    for co_line in inv.container_id.co_line_ids:
                        #Update landed cost on product form by volume. Ref: issues/3188 Date: 6 Sep 2015 => Here are we making average landed cost each time so we divide by two.
                        if co_line.product_id.landed_cost > 0.0:
                            #landed_cost = co_line.product_id.landed_cost + ((co_line.container_order_id.shipping_cost_by_volume * co_line.volume) / co_line.product_qty) / 2
                            landed_cost = (co_line.product_id.landed_cost + ((ship_cost_by_volume * co_line.volume) / co_line.product_qty)) / 2
                        else:# First time update on product form.
                            if co_line.product_qty > 0.0:
                                #landed_cost = (co_line.container_order_id.shipping_cost_by_volume * co_line.volume) / co_line.product_qty
                                landed_cost = (ship_cost_by_volume * co_line.volume) / co_line.product_qty
                        co_line.product_id.write({'landed_cost': landed_cost})
                flag = True
                for i in inv.container_id.invoice_ids:
                    if i.id != inv.id and i.state == 'draft':
                        flag = False
                if flag:
                    inv.container_id.action_done()
        return res

