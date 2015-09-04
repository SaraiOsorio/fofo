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
from datetime import datetime
import csv
import StringIO
import base64
import xlrd
import time
import sys
from openerp import tools
from _abcoll import ItemsView
from openerp.exceptions import except_orm, Warning, RedirectWarning


class sale_order(models.Model):
    _inherit = 'sale.order'
    
    is_lazada_order = fields.Boolean('Lazada Order?', readonly=True)
    lazada_order_no = fields.Char('Lazada Order Number', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            if self._context.get('is_lazada_order'):
                vals['name'] = self.env['ir.sequence'].get('sale.order.lazada') or '/'
        return super(sale_order, self).create(vals)

    @api.v7
    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        res = super(sale_order, self)._prepare_invoice(cr, uid, order, lines, context=context)
        res.update({'is_lazada_order':order.is_lazada_order, 'lazada_order_no': order.lazada_order_no })
        return res

class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
    is_lazada_order = fields.Boolean(related='sale_id.is_lazada_order', string='Lazada Order?' ,readonly=True)
    lazada_order_no = fields.Char(related='sale_id.lazada_order_no', string='Lazada Order Number' ,readonly=True)
    
    @api.v7
    def _get_invoice_vals(self, cr, uid, key, inv_type, journal_id, move, context=None):
        res = super(stock_picking, self)._get_invoice_vals(cr, uid, key, inv_type, journal_id, move, context=context)
        if move.picking_id.is_lazada_order:
            res.update({'is_lazada_order': move.picking_id.is_lazada_order, 'lazada_order_no': move.picking_id.lazada_order_no})
        return res
        
class stock_move(models.Model):
    _inherit = 'stock.move'
    
    is_lazada_order = fields.Boolean(related='picking_id.is_lazada_order', string='Lazada Order?' ,readonly=True)
    lazada_order_no = fields.Char(related='picking_id.lazada_order_no', string='Lazada Order Number' ,readonly=True)
    
    @api.v7
    def _get_invoice_line_vals(self, cr, uid, move, partner, inv_type, context=None):
        res = super(stock_move, self)._get_invoice_line_vals(cr, uid, move, partner, inv_type, context=context)
        res.update({'is_lazada_order': move.is_lazada_order, 'lazada_order_no': move.lazada_order_no})
        return res
        
class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    is_lazada_order = fields.Boolean(related='order_id.is_lazada_order', string='Lazada Order?' ,readonly=True)
    lazada_order_no = fields.Char(related='order_id.lazada_order_no', string='Lazada Order Number' ,readonly=True)
    
    #Override from base to pass the lazada order number and lazada order check box to invoice line from sale order
    @api.v7
    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        res = super(sale_order_line, self)._prepare_order_line_invoice_line(cr, uid, line, account_id=False, context=context)
        res.update({'is_lazada_order': line.is_lazada_order, 'lazada_order_no': line.lazada_order_no})
        return res
        
class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    is_lazada_order = fields.Boolean('Lazada Order?', readonly=True)
    lazada_order_no = fields.Char('Lazada Order Number', readonly=True)
    
    #probuse override from base to pass the lazada order number from invoice to journal entry(account.move)
    @api.multi
    def action_move_create(self):
        res = super(account_invoice, self).action_move_create()
        self.move_id.write({'lazada_order_no': self.lazada_order_no, 
                            'is_lazada_order': self.is_lazada_order})
        return res

class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'
    
    is_lazada_order = fields.Boolean(related='invoice_id.is_lazada_order', string='Lazada Order?' ,readonly=True)
    lazada_order_no = fields.Char(related='invoice_id.lazada_order_no', string='Lazada Order Number' ,readonly=True)


class account_move(models.Model):#probuse
    _inherit = 'account.move'
    
    is_lazada_order = fields.Boolean('Lazada Order?', readonly=True)
    lazada_order_no = fields.Char('Lazada Order Number', readonly=True)

class account_move_line(models.Model):#probuse
    _inherit = 'account.move.line'
    
    is_lazada_order = fields.Boolean(related='move_id.is_lazada_order', string='Lazada Order?' ,readonly=True)
    lazada_order_no = fields.Char(related='move_id.lazada_order_no', string='Lazada Order Number' ,readonly=True)

LAZADA_STATUS = {'pending': 1,'ready_to_ship' : 2, 'shipped': 3, 'delivered' : 4, 'failed' : 5, 'canceled' : 6}

class lazada_import(models.TransientModel):
    _name = 'lazada.import'

    input_file = fields.Binary('Lazada Order File (.xlsx format)')
    journal_id = fields.Many2one('account.journal', string='Sales Journal', required=True)

    @api.multi
    def import_orders(self):
        partner = self.env['ir.model.data'].get_object_reference('fofo_lazada', 'res_partner_lazada')[1]
        partner_data = self.env['sale.order'].onchange_partner_id(partner)
        sale_line_obj = self.env['sale.order.line']
        prod_obj = self.env['product.product']
        for line in self:
            try:
                lines = xlrd.open_workbook(file_contents=base64.decodestring(self.input_file))
            except IOError as e:
                raise Warning(_('Import Error!'),_(e.strerror))
            except ValueError as e:
                raise Warning(_('Import Error!'),_(e.strerror))
            except:
                e = sys.exc_info()[0]
                raise Warning(_('Import Error!'),_('Wrong file format. Please enter .xlsx file.'))
            
            product_dict = {}
            product_data_dict = {}
            sequene_counter = 0
            history_sequence = ''
            for sheet_name in lines.sheet_names(): 
                sheet = lines.sheet_by_name(sheet_name) 
                rows = sheet.nrows
                columns = sheet.ncols
                seller_sku = sheet.row_values(0).index('Seller SKU')
                created_at = sheet.row_values(0).index('Created at')
                order_number = sheet.row_values(0).index('Order Number')
                unit_price = sheet.row_values(0).index('Unit Price')
                status = sheet.row_values(0).index('Status')
                
                items_dict = {}
                seller_sku_list = []
                picking_to_transfer = []
                picking_to_invoice = []
                for row_no in range(rows):
                    if row_no > 0:
                        seller_sku_value = sheet.row_values(row_no)[seller_sku] # "Seller SKU" from xlsx
                        if not seller_sku_value in seller_sku_list:
                            products = prod_obj.search([('default_code', '=', seller_sku_value)]).id
                            seller_sku_list.append(seller_sku_value)
                            if not product_dict.get(seller_sku_value):
                                product_dict[seller_sku_value] = products
                            
                            if product_dict.get(seller_sku_value):
                                product_id = product_dict.get(seller_sku_value)
                                product_data = sale_line_obj.product_id_change(partner_data['value']['pricelist_id'], product_id, qty=0,
                                uom=False, qty_uos=0, uos=False, name='', partner_id=partner,
                                lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False)
                                
                                if not product_data_dict.get(product_id):
                                    product_data_dict[product_id] = product_data
                        order = str(sheet.row_values(row_no)[order_number]).split('.')[0]
                        if not items_dict.get(order):
                            items_dict[order] = [{'seller_sku' : seller_sku_value,
                                                                                       'created_at' : sheet.row_values(row_no)[created_at],
                                                                                       'unit_price' : sheet.row_values(row_no)[unit_price], 
                                                                                       'status' : sheet.row_values(row_no)[status],
                                                                                       'order_no' : order }]
                        else:
                            items_dict[order].append({'seller_sku' : seller_sku_value,
                                                                                       'created_at' : sheet.row_values(row_no)[created_at],
                                                                                       'unit_price' : sheet.row_values(row_no)[unit_price], 
                                                                                       'status' : sheet.row_values(row_no)[status],
                                                                                       'order_no' : order })
                result ={}
                import_date = time.strftime('%Y-%m-%d')
                history_ids = []
                ctx = self._context.copy()
                for item in items_dict:
                    no_order_number = False
                    order_fail = False
                    date_convert = tools.ustr(items_dict[item][0]['created_at'])
                    final_date = datetime.strptime(date_convert, '%Y-%m-%d %H:%M:%S').strftime('%m/%d/%Y %H:%M:%S')
                    #this section will check if any product is not found then it will not create orderline for that product and also create the history with fail status
                    for line_sku in items_dict[item]:
                        date_convert_new = tools.ustr(line_sku['created_at'])
                        final_date_new = datetime.strptime(date_convert_new, '%Y-%m-%d %H:%M:%S').strftime('%m/%d/%Y %H:%M:%S')
                        if not line_sku['order_no']:
                            no_order_number = True
                        if not product_dict[line_sku['seller_sku']]:
                            order_fail = True
                            history_vals = {
                                    'product_id':False,
                                    'seller_sku':line_sku['seller_sku'],
                                    'created_at':final_date_new,
                                    'order_number':line_sku['order_no'],#order,
                                    'unit_price': line_sku['unit_price'], #sheet.row_values(row_no)[unit_price],
                                    'status': line_sku['status'],#sheet.row_values(row_no)[status],
                                    'import_time':import_date,
                                    'user_id': self.env.user.id,
                                    'order_status':'fail',
                                    'notes': 'Product/SKU not found in ERP system.'
                            }
                            history = self.env['import.history'].create(history_vals)
                            if sequene_counter == 0:
                                history_sequence = self.env['ir.sequence'].get('lazada.import.history')
                                sequene_counter += 1
                            history.name = history_sequence
                            if history:
                                history_ids.append(history.id)
                    if order_fail:
                        continue
                    
                    exist_orders = self.env['sale.order'].search([('lazada_order_no', '=', items_dict[item][0]['order_no'])])
                    
                    flag_order_exist = False
                    #this section will check if order is already created
                    if exist_orders:
                        exist_orders = exist_orders[0]
                        flag_order_exist = True
                        if exist_orders.order_line:
                            history_lines = self.env['import.history'].search([('sale_line_id', 'in', exist_orders.order_line.ids)])
                            for history in history_lines:
                                #here will check if order exist and state changed in file then update the state of order in Odoo
                                #if order tries to move to reverse state then it will stop it and create the history with fail status
                                for line_status in items_dict[item]:
                                    
                                    old_status = LAZADA_STATUS[str(history.status)]
                                    new_status = LAZADA_STATUS[str(line_status['status'])]
                                    
                                    if new_status < old_status:
                                        history.order_status = 'fail'
                                        history.notes = 'Invalid State Movement'
                                        history_ids.append(history.id)
                                    else:
                                        if not str(history.status) == str(line_status['status']):
                                            if str(line_status['status']) == 'ready_to_ship':#Ready to Tranfer in Odoo.
                                                exist_orders.signal_workflow('order_confirm')
                                                if exist_orders.picking_ids:
                                                    for picking in exist_orders.picking_ids:
                                                        picking.write({'invoice_state': '2binvoiced'})
                                                        pick = picking.force_assign()
                                            #If Order has status pending then set
                                            #Delivery order in draft state
                                            if str(line_status['status']) == 'pending':
                                                exist_orders.signal_workflow('order_confirm')
                                                if exist_orders.picking_ids:
                                                    for picking in exist_orders.picking_ids:
                                                        picking.write({'invoice_state': '2binvoiced'})
                                                        
                                            #If Order has status failed then set
                                            #Delivery order in ready to transfer and then set that order to cancel state state
                                            if str(line_status['status']) == 'failed':
                                                exist_orders.signal_workflow('order_confirm')
                                                if exist_orders.picking_ids:
                                                    for picking in exist_orders.picking_ids:
                                                        picking.write({'invoice_state': '2binvoiced'})
                                                        pick_id = picking.force_assign()
                                                        cancel_pick = picking.action_cancel()
                                            
                                            #If Order has status shipped then set
                                            #Delivery order in transferred state but no need to create invoice
                                            if str(line_status['status']) == 'shipped':
                                                exist_orders.signal_workflow('order_confirm')
                                                if exist_orders.picking_ids:
                                                    for picking in exist_orders.picking_ids:
                                                        picking.write({'invoice_state': '2binvoiced'})
                                                        picking_to_transfer.append(picking.id)
                                            
                                            #If Order has status delivered in excel file then make sale order to done state
                                            #Delivery order in transferred and invoice validated
                                            if str(line_status['status']) == 'delivered':
                                                exist_orders.signal_workflow('order_confirm')
                                                if exist_orders.picking_ids:
                                                    for picking in exist_orders.picking_ids:
                                                        picking.write({'invoice_state': '2binvoiced'})
                                                        picking_to_transfer.append(picking.id)
                                                        picking_to_invoice.append(picking.id)
                                            
                                            if str(line_status['status']) == 'canceled':
                                                exist_orders.signal_workflow('order_confirm')
                                                exist_orders.action_cancel()
                                            
                                            history.status = line_status['status']
                                            history_ids.append(history.id)
                    if flag_order_exist:
                        continue
                    date_convert = tools.ustr(items_dict[item][0]['created_at'])
                    final_date = datetime.strptime(date_convert, '%Y-%m-%d %H:%M:%S').strftime('%m/%d/%Y %H:%M:%S')
                    sale_order_id = False
                    #If any line in file does not have order number then system will not create the sale order for that order number.
                    #also it create the history with fails status
                    if no_order_number:
                        history_vals = {
                            'product_id':False,
                            'seller_sku':seller_sku_value,
                            'created_at':final_date,
                            'order_number':'',
                            'unit_price':sheet.row_values(row_no)[unit_price],
                            'status':sheet.row_values(row_no)[status],
                            'import_time':import_date,
                            'user_id':self.env.user.id,
                            'order_status':'fail',
                            'notes': 'Missing order number in the ERP system.'
                        }
                        history = self.env['import.history'].create(history_vals)
                        if sequene_counter == 0:
                            history_sequence = self.env['ir.sequence'].get('lazada.import.history')
                            sequene_counter += 1
                        history.name = history_sequence
                        if history:
                            history_ids.append(history.id)
                    else:
                        ordervals = {
                            'name' : '/',
                            'client_order_ref': item,
                            'partner_invoice_id' : partner_data['value']['partner_invoice_id'],
                            'date_order' : final_date,
                            'partner_id' : partner,
                            'pricelist_id' : partner_data['value']['pricelist_id'],
                            'partner_shipping_id' : partner_data['value']['partner_shipping_id'],
                            'payment_term': partner_data['value']['payment_term'],
                            'state' : 'draft',
                            'is_lazada_order': True,
                            'order_policy' :  'picking',
                            'lazada_order_no': items_dict[item][0]['order_no'],#probuse
                        }
                        ctx.update({'is_lazada_order': True})
                        sale_order_id = self.env['sale.order'].with_context(ctx).create(ordervals)
                    
                    #TO DO: If one csv already imported in past then csv does not re-import again
                    #TODO: If any lazada product is not found in openerp then that sale order must be in draft state  
                    #if sale order created successfully then create the orderlines for particular sale order.
                    if sale_order_id:
                        for i in items_dict[item]:
                            products = product_dict[i['seller_sku']]
                            #if any line does not found product then it will not create the orderline for that product and create the history with fail status for that line
                            if products:
                                product_data = product_data_dict[products]
                                orderlinevals = {
                                        'order_id' : sale_order_id.id,
                                        'product_uom_qty' : 1.0,
                                        'product_uom' : product_data['value']['product_uom'],
                                        'name' : product_data['value']['name'],
                                        'price_unit' : i['unit_price'],
                                        'invoiced' : False,
                                        'state' : 'draft',
                                        'product_id' : products,
                                        'tax_id' : product_data['value']['tax_id'],
                                        'is_lazada_order': True,
                                        'lazada_order_no': order,
                                            }
                                line_id = sale_line_obj.create(orderlinevals)
                                history_vals = {
                                    'product_id':products,
                                    'seller_sku':seller_sku_value,
                                    'created_at':final_date,
                                    'order_number':i['order_no'],
                                    'unit_price':sheet.row_values(row_no)[unit_price],
                                    'status':i['status'],
                                    'import_time':import_date,
                                    'user_id':self.env.user.id,
                                    'order_status':'done',
                                    'sale_line_id': line_id.id
                                }
                                history = self.env['import.history'].create(history_vals)
                                if sequene_counter == 0:
                                    history_sequence = self.env['ir.sequence'].get('lazada.import.history')
                                    sequene_counter += 1
                                history.name = history_sequence
                                if history:
                                    history_ids.append(history.id)
                            else:#Unsed now ? Since we already check for fail at begining.
                                history_vals = {
                                        'product_id':False,
                                        'seller_sku':seller_sku_value,
                                        'created_at':final_date,
                                        'order_number':order,
                                        'unit_price':sheet.row_values(row_no)[unit_price],
                                        'status':sheet.row_values(row_no)[status],
                                        'import_time':import_date,
                                        'user_id':self.env.user.id,
                                        'order_status':'fail',
                                        'notes': 'missing product'
                                }
                                history = self.env['import.history'].create(history_vals)
                                if sequene_counter == 0:
                                    history_sequence = self.env['ir.sequence'].get('lazada.import.history')
                                    sequene_counter += 1
                                history.name = history_sequence
                                if history:
                                    history_ids.append(history.id)
                        #below section will set the state of sale order related to lazada status
                        
                        if i['status'] == 'ready_to_ship':
                            sale_order_id.signal_workflow('order_confirm')
                            if sale_order_id.picking_ids:
                                for picking in sale_order_id.picking_ids:
                                    picking.write({'invoice_state': '2binvoiced'})
                                    pick = picking.force_assign()
                        #If Order has status pending then set
                        #Delivery order in draft state
                        if i['status'] == 'pending':
                            sale_order_id.signal_workflow('order_confirm')
                            if sale_order_id.picking_ids:
                                for picking in sale_order_id.picking_ids:
                                    picking.write({'invoice_state': '2binvoiced'})
                        #If Order has status failed then set
                        #Delivery order in ready to transfer and then set that order to cancel state state
                        if i['status'] == 'failed':
                            sale_order_id.signal_workflow('order_confirm')
                            if sale_order_id.picking_ids:
                                for picking in sale_order_id.picking_ids:
                                    picking.write({'invoice_state': '2binvoiced'})
                                    pick_id = picking.force_assign()
                                    cancel_pick = picking.action_cancel()
                        #If Order has status shipped then set
                        #Delivery order in transferred state but no need to create invoice
                        if i['status'] == 'shipped':
                            sale_order_id.signal_workflow('order_confirm')
                            if sale_order_id.picking_ids:
                                for picking in sale_order_id.picking_ids:
                                    picking.write({'invoice_state': '2binvoiced'})
                                    picking_to_transfer.append(picking.id)
                        #If Order has status delivered in excel file then make sale order to done state
                        #Delivery order in transferred and invoice validated
                        if i['status'] == 'delivered':
    #                             if items_dict[item][0]['status'] == 'delivered':
                            sale_order_id.signal_workflow('order_confirm')
                            if sale_order_id.picking_ids:
                                for picking in sale_order_id.picking_ids:
                                    picking.write({'invoice_state': '2binvoiced'})
                                    picking_to_transfer.append(picking.id)
                                    picking_to_invoice.append(picking.id)
                        
                        if i['status'] == 'canceled':
                            sale_order_id.signal_workflow('order_confirm')
                            sale_order_id.action_cancel()
                            
                    
                    #If Order has status Ready to Ship then set
                    #Delivery order in ready to transfer state
            pick_transfer = self.env['stock.picking'].browse(picking_to_transfer)
            #it will transfer the created DO
            pick_transfer.do_transfer()
            context = self._context.copy()
            context['inv_type'] = 'out_invoice'
            pick_invoice = self.env['stock.picking'].browse(picking_to_invoice)
            #It will create the invoice on base of DO
            invoice = pick_invoice.with_context(context).action_invoice_create(
                                            journal_id = self.journal_id.id,
                                            group = False,
                                            type = 'out_invoice',
                                            )
            if invoice:
                for i in invoice:
                    #It will validate the created invoice
                    invoice_data = self.env['account.invoice'].browse(i)
                    invoice_data.signal_workflow('invoice_open')
            result = self.env.ref('fofo_lazada.lazada_import_history_action')
            result = result.read()[0]
            result['context'] = {'search_default_failed': 1}
            result['domain'] = str([('id','in',history_ids)])
            #return the list view of history (only failed order)
            return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
