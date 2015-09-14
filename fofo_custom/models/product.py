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
from openerp import api, tools, SUPERUSER_ID
from openerp.tools.float_utils import float_round

class product_packaging(models.Model):
    _inherit = "product.packaging"
    
    @api.one
    @api.depends('qty', 'ul')
    def _compute_volume(self):
        height = self.ul.height
        width = self.ul.width
        length = self.ul.length
        qty1 = self.qty
        if qty1 > 0:
            self.volume = (height*width*length)/1000000/qty1
            
    @api.one
    @api.depends('qty', 'ul')
    def _compute_gross_weight(self):
        plu_gross_weight = self.ul.plu_gross_weight
        qty = self.qty
        if qty > 0:
            self.weight_gross = plu_gross_weight/qty
    
    volume = fields.Float(compute='_compute_volume', string='Volume', digits=dp.get_precision('Product Volume'))
    weight_gross = fields.Float(compute='_compute_gross_weight', digits=dp.get_precision('Stock Weight') , string='Gross Weight')
    weight_net = fields.Float('Net Weight', digits=dp.get_precision('Stock Weight'), help="The net weight in Kg.")

class product_template(models.Model):
    _inherit = 'product.template'

    @api.one
    @api.depends('product_variant_ids','product_variant_ids.incoming_contained_qty', 'product_variant_ids.incoming_not_contained_qty')
    def _count_incoming_contained_qty(self):
        contained_qty = 0.0
        not_contained_qty = 0.0
        for product in self.product_variant_ids:
            contained_qty += product.incoming_contained_qty
            not_contained_qty += product.incoming_not_contained_qty
        self.incoming_contained_qty = contained_qty
        self.incoming_not_contained_qty = not_contained_qty

    @api.one
    @api.depends('product_variant_ids','product_variant_ids.landed_cost')
    def _get_landed_cost(self):
        cost_sum = 0.0
        counter = 0
        for cost in self.product_variant_ids:
            cost_sum += cost.landed_cost
            counter += 1
        self.landed_cost_all = cost_sum / counter #Average landed cost. #TODO: need to check cost price method: 1. Standard price 2. Avg price 3 Real price. ? If option 2 is selected then only do average? 
    
    @api.one
    @api.depends('product_variant_ids','product_variant_ids.total_standard_landed')
    def _total_cost_call(self):
        #cost_sum = 0.0
        #for cost in self.product_variant_ids:
        #    cost_sum += cost.total_standard_landed
        #self.total_cost_call = cost_sum
        self.total_cost_call = self.standard_price + self.landed_cost_all

    sale_line_ids = fields.One2many('sale.order.line', 'product_tmpl_id_store', 'Sales History')
    landed_cost_all = fields.Float(compute=_get_landed_cost, string='Landed Cost')
    total_cost_call = fields.Float(compute=_total_cost_call, string='Total Cost')
    shipping_ok = fields.Boolean('Shipping Product', help="Specify if the product can be selected in a container order as shipping product.")
    incoming_contained_qty = fields.Float(compute='_count_incoming_contained_qty', string='Incoming (Contained)', copy=False, digits=dp.get_precision('Product Unit of Measure'), readonly=True, store=True, help='This will show the total draft picking-in with Container Orders.')
    incoming_not_contained_qty = fields.Float(compute='_count_incoming_contained_qty', string='Incoming (Not-Contained)', copy=False, digits=dp.get_precision('Product Unit of Measure'), readonly=True, store=True, help='This will show the total draft picking-in without Container Orders.')

class product_product(models.Model):
    _inherit = 'product.product'

    @api.one
    @api.depends('description', 'purchase_line_ids', 'purchase_line_ids.state', 'purchase_line_ids.product_id', 'purchase_line_ids.remain_contain_qty', 'container_line_ids', 'container_line_ids.state', 'container_line_ids.product_qty')# todo should be updated when incoming shipment created from CO.
    def _count_qty_contained(self):
        #This method will set the value of contained qty and total forecasted with contained qty. It will consider only draft container orders.
        self.qty_contained = 0.0
        if self.ids:
            self._cr.execute('''SELECT
                    COALESCE(sum(l.product_qty), 0.0)
                FROM
                    container_order_line l
                LEFT JOIN
                    container_order c on (c.id=l.container_order_id) 
                LEFT JOIN
                    product_product p on (p.id=l.product_id)
                WHERE
                    c.state = %s and p.id IN %s group by p.id''',('draft', tuple(self.ids),))
            res = self._cr.fetchall()
            if res and res[0]:
                self.qty_contained = res[0][0]
        self.virtual_qty_contained = self.virtual_available + self.qty_contained
    
    @api.one
    @api.depends('standard_price', 'landed_cost')
    def _compute_total_cost(self):
        self.total_standard_landed = self.standard_price + self.landed_cost #we can directly use standard_price.

    @api.one
    @api.depends('description', 'purchase_line_ids', 'purchase_line_ids.state', 'purchase_line_ids.product_id', 'purchase_line_ids.remain_contain_qty', 'container_line_ids', 'container_line_ids.state', 'container_line_ids.product_qty')
    def _count_incoming_contained_qty(self):
        ctx = dict(self._context or {})
        domain_products = [('product_id', 'in', self.ids)]
        domain_quant, domain_move_in, domain_move_out = [], [], []
        domain_move_in_contain = []
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self.with_context(ctx)._get_domain_locations()
        domain_move_in += self.with_context(ctx)._get_domain_dates() + [('state', 'not in', ('done', 'cancel', 'draft')), ('is_related_co', '=', False)] + domain_products
        domain_move_in_contain += self.with_context(ctx)._get_domain_dates() + [('state', 'not in', ('done', 'cancel', 'draft')), ('is_related_co', '=', True)] + domain_products

        if self._context.get('owner_id'):
            owner_domain = ('restrict_partner_id', '=', self._context['owner_id'])
            domain_move_in.append(owner_domain)
            domain_move_in_contain.append(owner_domain)

        domain_move_in += domain_move_in_loc
        domain_move_in_contain += domain_move_in_loc
        moves_in = self.env['stock.move'].read_group(domain_move_in, ['product_id', 'product_qty'], ['product_id'])
        moves_in_contain = self.env['stock.move'].read_group(domain_move_in_contain, ['product_id', 'product_qty'], ['product_id'])

        moves_in = dict(map(lambda x: (x['product_id'][0], x['product_qty']), moves_in))
        moves_in_contain = dict(map(lambda x: (x['product_id'][0], x['product_qty']), moves_in_contain))
        res = {}
        for product in self:
            id = product.id
            self.incoming_contained_qty = float_round(moves_in_contain.get(id, 0.0), precision_rounding=product.uom_id.rounding)
            self.incoming_not_contained_qty = float_round(moves_in.get(id, 0.0), precision_rounding=product.uom_id.rounding)
#Columns
    qty_contained = fields.Float(compute=_count_qty_contained, string='Contained Quantity', copy=False, digits=dp.get_precision('Product Unit of Measure'), readonly=True, store=True, help='This will show the total contained qty of draft container orders.') # Show total qty in purchase order lines from container order which are draft container order (not confirmed yet.).
    virtual_qty_contained = fields.Float(compute=_count_qty_contained, string='Forcasted Quantity  (Contained)',help='Forcasted Quantity + Contained Quantity.', copy=False, digits=dp.get_precision('Product Unit of Measure'), readonly=True, store=True) 
    purchase_line_ids = fields.One2many('purchase.order.line', 'product_id', string='Purchase Lines')
    container_line_ids = fields.One2many('container.order.line', 'product_id', string='Container Order Lines')
    length =  fields.Float('Length')#unused todo remove
    height =  fields.Float('Height')#unused todo remove
    width =  fields.Float('Width')#unused todo remove
    landed_cost = fields.Float('Landed Cost')
    total_standard_landed = fields.Float(compute=_compute_total_cost, string='Total Cost', help='Standard Cost + Landed Cost')
    sale_line_ids = fields.One2many('sale.order.line', 'product_id', 'Sales History')
    incoming_contained_qty = fields.Float(compute='_count_incoming_contained_qty', string='Incoming (Contained)', copy=False, digits=dp.get_precision('Product Unit of Measure'), readonly=True, store=True, help='This will show the total draft picking-in with Container Orders.')
    incoming_not_contained_qty = fields.Float(compute='_count_incoming_contained_qty', string='Incoming (Not-Contained)', copy=False, digits=dp.get_precision('Product Unit of Measure'), readonly=True, store=True, help='This will show the total draft picking-in without Container Orders.')



class product_ul(models.Model):
    _inherit = 'product.ul'
    
    plu_gross_weight = fields.Float('PLU Gross Weight', digits=dp.get_precision('Stock Weight'),help="Total weight of product and package in kg.")
    
class product_template(models.Model):
    _inherit = 'product.template'
    
    @api.one
    @api.depends('packaging_ids','packaging_ids.qty', 'packaging_ids.ul')
    def _compute_volume(self):
        if not self.packaging_ids:
            self.volume = 0.0
        else:
            height = self.packaging_ids[0].ul.height
            width = self.packaging_ids[0].ul.width
            length = self.packaging_ids[0].ul.length
            qty1 = self.packaging_ids[0].qty
            if qty1 > 0:
                self.volume = (height*width*length)/1000000/qty1
            
    @api.one
    @api.depends('packaging_ids','packaging_ids.qty', 'packaging_ids.ul')
    def _compute_gross_weight(self):
        if not self.packaging_ids:
            self.weight = 0.0
        else:
            plu_gross_weight = self.packaging_ids[0].ul.plu_gross_weight
            qty = self.packaging_ids[0].qty
            if qty > 0:
                self.weight = plu_gross_weight/qty

    volume = fields.Float(string='Volume', compute='_compute_volume', digits=dp.get_precision('Product Volume'), store=True)
    weight = fields.Float(string='Gross Weight', compute='_compute_gross_weight', digits=dp.get_precision('Stock Weight'), store=True)
    weight_net = fields.Float(string='Net Weight', digits=dp.get_precision('Stock Weight'))
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
