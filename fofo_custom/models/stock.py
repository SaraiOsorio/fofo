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

class stock_quant(models.Model):
    _inherit = 'stock.quant'

    @api.v7 # Override here to pass partner_id from stock move since for container order case there is no partner on picking.!
    def _prepare_account_move_line(self, cr, uid, move, qty, cost, credit_account_id, debit_account_id, context=None):
        res = super(stock_quant, self)._prepare_account_move_line(cr, uid, move, qty, cost, credit_account_id, debit_account_id, context=context)
        for line in res:
            if line[2] and 'partner_id' in line[2] and not line[2]['partner_id']:
                if move.co_line_id:
                    line[2]['partner_id'] = move.partner_id and move.partner_id.id or False
        return res

class procurement_order(models.Model):
    _inherit = 'procurement.order'

    #Only use supplier description in po line name.
    def _get_po_line_values_from_proc(self, cr, uid, procurement, partner, company, schedule_date, context=None):
        if context is None:
            context = {}
        res = super(procurement_order, self)._get_po_line_values_from_proc(cr, uid, procurement, partner, company, schedule_date, context=context)

        prod_obj = self.pool.get('product.product')
        new_context = context.copy()
        new_context.update({'lang': partner.lang, 'partner_id': partner.id})
        product = prod_obj.browse(cr, uid, procurement.product_id.id, context=new_context)
        if product.description_purchase:
            name = product.description_purchase
            res.update({'name': name})
        return res

class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
    container_id = fields.Many2one('container.order', string="Container Reference")
    
    #Below method is completely override here to pass container_id to invoice..
    @api.v7
    def _invoice_create_line(self, cr, uid, moves, journal_id, inv_type='out_invoice', context=None):
        invoice_obj = self.pool.get('account.invoice')
        move_obj = self.pool.get('stock.move')
        invoices = {}
        is_extra_move, extra_move_tax = move_obj._get_moves_taxes(cr, uid, moves, inv_type, context=context)#TODO check.
        for move in moves:
            company = move.company_id
            origin = move.picking_id.name
            partner, user_id, currency_id = move_obj._get_master_data(cr, uid, move, company, context=context)

            key = (partner, currency_id, company.id, user_id)
            invoice_vals = self._get_invoice_vals(cr, uid, key, inv_type, journal_id, move, context=context)

            if key not in invoices:
                # Get account and payment terms


                
                if move.picking_id and move.picking_id.container_id:#Ecosoft
                    invoice_vals.update({'container_id': move.picking_id.container_id.id})#Ecosoft


                invoice_id = self._create_invoice_from_picking(cr, uid, move.picking_id, invoice_vals, context=context)
                invoices[key] = invoice_id
            else:
                invoice = invoice_obj.browse(cr, uid, invoices[key], context=context)
                if not invoice.origin or invoice_vals['origin'] not in invoice.origin.split(', '):
                    invoice_origin = filter(None, [invoice.origin, invoice_vals['origin']])
                    invoice.write({'origin': ', '.join(invoice_origin)})

            invoice_line_vals = move_obj._get_invoice_line_vals(cr, uid, move, partner, inv_type, context=context)
            invoice_line_vals['invoice_id'] = invoices[key]
            invoice_line_vals['origin'] = origin
            if is_extra_move[move.id] and extra_move_tax[move.picking_id, move.product_id]:
                invoice_line_vals['invoice_line_tax_id'] = extra_move_tax[move.picking_id, move.product_id]

            move_obj._create_invoice_line_from_vals(cr, uid, move, invoice_line_vals, context=context)
            move_obj.write(cr, uid, move.id, {'invoice_state': 'invoiced'}, context=context)

        invoice_obj.button_compute(cr, uid, invoices.values(), context=context, set_total=(inv_type in ('in_invoice', 'in_refund')))
        return invoices.values()
    
    @api.v7
    def _get_invoice_vals(self, cr, uid, key, inv_type, journal_id, move, context=None):
#       Invoice Date = Loading date from Container Order. (Not receiving date as standard)
        inv_vals = super(stock_picking, self)._get_invoice_vals(cr, uid, key, inv_type, journal_id, move, context=context)
        if move.picking_id and move.picking_id.container_id:
            inv_vals.update({
                'date_invoice': move.picking_id.container_id.load_date or False,
                })
        return inv_vals


class stock_move(models.Model):
    _inherit = 'stock.move'
    
    @api.v7 #Override from base.
    def action_cancel(self, cr, uid, ids, context=None):
        res = super(stock_move, self).action_cancel(cr, uid, ids, context)
        for move in self.browse(cr, uid, ids, context):
            if move.co_line_id and move.purchase_line_id:
                if move.purchase_line_id.state == 'contained':
                    self.pool.get('purchase.order.line').write(cr, uid, [move.purchase_line_id.id], {'state': 'confirmed'}) #If picking cancel then change the state of its related purchsae order lines to confirmed. This will alllow again selection of that purchase line in new container order.
        return res

#columns
    co_line_id = fields.Many2one('container.order.line', string='Container Order Line')
    number_packages =  fields.Integer(string='Total Number of Packages')
    qty_package = fields.Float(string='Quantity / Package')
 
class stock_pack_operation(models.Model):
    _inherit = 'stock.pack.operation'

    @api.one
    @api.depends('linked_move_operation_ids', 'linked_move_operation_ids.move_id', 'linked_move_operation_ids.qty')
    def _get_package(self):
        self.number_packages = 0
        self.qty_package = 0.0
        for line in self:
            total_pack = 0.0
            qty_pack = 0.0
            for link_move in line.linked_move_operation_ids:
                total_pack += link_move.move_id.number_packages
                qty_pack += link_move.move_id.qty_package
            self.number_packages = total_pack
            self.qty_package = qty_pack

#columns    
    number_packages =  fields.Integer(compute=_get_package, string='Total Number of Packages', store=True)
    qty_package = fields.Float(compute=_get_package, string='Quantity / Package', store=True)
 
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
