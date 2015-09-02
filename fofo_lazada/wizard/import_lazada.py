from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from datetime import datetime
import csv
import StringIO
import base64
import xlrd
from openerp import tools
from _abcoll import ItemsView


class sale_order(models.Model):
    _inherit = 'sale.order'
    
    is_lazada_order = fields.Boolean('Lazada Order?', readonly=True)
    lazada_order_no = fields.Char('Lazada Order Number', readonly=False)

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
    
#     is_lazada_order = fields.Boolean('Lazada Order?', readonly=True)
#     lazada_order_no = fields.Char('Lazada Order Number', readonly=True)
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


class lazada_import(models.TransientModel):
    _name = 'lazada.import'

    input_file = fields.Binary('Input File')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)

    @api.multi
    def import_orders(self):
        partner = self.env['ir.model.data'].get_object_reference('fofo_lazada', 'res_partner_lazada')[1]
        partner_data = self.env['sale.order'].onchange_partner_id(partner)
        for line in self:
            lines = xlrd.open_workbook(file_contents=base64.decodestring(self.input_file))
            product_dict = {}
            product_data_dict = {}
            for sheet_name in lines.sheet_names(): 
                sheet = lines.sheet_by_name(sheet_name) 
                rows = sheet.nrows
                columns = sheet.ncols
                #sheet.row_values(row)[column]
                
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
                        if not sheet.row_values(row_no)[seller_sku] in seller_sku_list:
                            products = self.env['product.product'].search([('default_code', '=', sheet.row_values(row_no)[seller_sku])]).id
                            seller_sku_list.append(sheet.row_values(row_no)[seller_sku])
                            if not product_dict.get(sheet.row_values(row_no)[seller_sku]):
                                product_dict[sheet.row_values(row_no)[seller_sku]] = products
                            
                            if product_dict.get(sheet.row_values(row_no)[seller_sku]):
                                product_id = product_dict.get(sheet.row_values(row_no)[seller_sku])
                                product_data = self.env['sale.order.line'].product_id_change(partner_data['value']['pricelist_id'], product_id, qty=0,
                                uom=False, qty_uos=0, uos=False, name='', partner_id=partner,
                                lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False)
                                
                                if not product_data_dict.get(product_id):
                                    product_data_dict[product_id] = product_data
                        
                        if not items_dict.get(int(sheet.row_values(row_no)[order_number])):
                            items_dict[int(sheet.row_values(row_no)[order_number])] = [{'seller_sku' : sheet.row_values(row_no)[seller_sku],
                                                                                       'created_at' : sheet.row_values(row_no)[created_at],
                                                                                       'unit_price' : sheet.row_values(row_no)[unit_price], 
                                                                                       'status' : sheet.row_values(row_no)[status],
                                                                                       'order_no' : int(sheet.row_values(row_no)[order_number]) }]
                        else:
                            items_dict[int(sheet.row_values(row_no)[order_number])].append({'seller_sku' : sheet.row_values(row_no)[seller_sku],
                                                                                       'created_at' : sheet.row_values(row_no)[created_at],
                                                                                       'unit_price' : sheet.row_values(row_no)[unit_price], 
                                                                                       'status' : sheet.row_values(row_no)[status],
                                                                                       'order_no' : int(sheet.row_values(row_no)[order_number]) })
                result ={}
                import_date = datetime.now().strftime('%m/%d/%Y %H:%M:%S')
                history_ids = []
                ctx = self._context.copy()
                for item in items_dict:
                    date_convert = tools.ustr(items_dict[item][0]['created_at'])
                    final_date = datetime.strptime(date_convert, '%Y-%m-%d %H:%M:%S').strftime('%m/%d/%Y %H:%M:%S')
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
#                         'lazada_order_no': int(sheet.row_values(row_no)[order_number]),#probuse
                        'lazada_order_no': items_dict[item][0]['order_no'],#probuse
                    }
                    ctx.update({'is_lazada_order': True})
                    
                    sale_order_id = self.env['sale.order'].with_context(ctx).create(ordervals)
                    
                    #TO DO: If one csv already imported in past then csv does not re-import again
                    #TODO: If any lazada product is not found in openerp then that sale order must be in draft state  
                    
                    for i in items_dict[item]:
                        products = product_dict[i['seller_sku']]
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
                                    'lazada_order_no': int(sheet.row_values(row_no)[order_number]),
                                        }
                            line_id = self.env['sale.order.line'].create(orderlinevals)
                            history_vals = {
                                'product_id':products,
                                'seller_sku':sheet.row_values(row_no)[seller_sku],
                                'created_at':final_date,
                                'order_number':int(sheet.row_values(row_no)[order_number]),
                                'unit_price':sheet.row_values(row_no)[unit_price],
                                'status':sheet.row_values(row_no)[status],
                                'import_time':import_date,
                                'user_id':self.env.user.id,
                                'order_status':'done',
                                'sale_line_id': line_id.id
                            }
                            if items_dict[item][0]['status'] == 'ready_to_ship':
                                sale_order_id.signal_workflow('order_confirm')
                                if sale_order_id.picking_ids:
                                    for picking in sale_order_id.picking_ids:
                                        picking.write({'invoice_state': '2binvoiced'})
                                        pick = picking.force_assign()
                            
                            #If Order has status pending then set
                            #Delivery order in draft state
                            if items_dict[item][0]['status'] == 'pending':
                                sale_order_id.signal_workflow('order_confirm')
                                if sale_order_id.picking_ids:
                                    for picking in sale_order_id.picking_ids:
                                        picking.write({'invoice_state': '2binvoiced'})
                                        
                            #If Order has status failed then set
                            #Delivery order in ready to transfer and then set that order to cancel state state
                            if items_dict[item][0]['status'] == 'failed':
                                sale_order_id.signal_workflow('order_confirm')
                                if sale_order_id.picking_ids:
                                    for picking in sale_order_id.picking_ids:
                                        picking.write({'invoice_state': '2binvoiced'})
                                        pick_id = picking.force_assign()
                                        cancel_pick = picking.action_cancel()
                            
                            #If Order has status shipped then set
                            #Delivery order in transferred state but no need to create invoice
                            if items_dict[item][0]['status'] == 'shipped':
                                sale_order_id.signal_workflow('order_confirm')
                                if sale_order_id.picking_ids:
                                    for picking in sale_order_id.picking_ids:
                                        picking.write({'invoice_state': '2binvoiced'})
                                        picking_to_transfer.append(picking.id)
                            
                            #If Order has status delivered in excel file then make sale order to done state
                            #Delivery order in transferred and invoice validated
                            
                            if items_dict[item][0]['status'] == 'delivered':
                                sale_order_id.signal_workflow('order_confirm')
                                if sale_order_id.picking_ids:
                                    for picking in sale_order_id.picking_ids:
                                        picking.write({'invoice_state': '2binvoiced'})
                                        picking_to_transfer.append(picking.id)
                                        picking_to_invoice.append(picking.id)
                        else:
                            history_vals = {
                                    'product_id':False,
                                    'seller_sku':sheet.row_values(row_no)[seller_sku],
                                    'created_at':final_date,
                                    'order_number':int(sheet.row_values(row_no)[order_number]),
                                    'unit_price':sheet.row_values(row_no)[unit_price],
                                    'status':sheet.row_values(row_no)[status],
                                    'import_time':import_date,
                                    'user_id':self.env.user.id,
                                    'order_status':'fail',
                                    'notes': 'missing product'
                            }
                    history = self.env['import.history'].create(history_vals)
                    if history:
                        history_ids.append(history.id)
                    result = self.env.ref('fofo_lazada.lazada_import_history_action')
                    result = result.read()[0]
                    result['context'] = {}
                    #If Order has status Ready to Ship then set
                    #Delivery order in ready to transfer state
            pick_transfer = self.env['stock.picking'].browse(picking_to_transfer)
            
            pick_transfer.do_transfer()
            context = self._context.copy()
            context['inv_type'] = 'out_invoice'
            pick_invoice = self.env['stock.picking'].browse(picking_to_invoice)
            invoice = pick_invoice.with_context(context).action_invoice_create(
                                            journal_id = self.journal_id.id,
                                            group = False,
                                            type = 'out_invoice',
                                            )
            if invoice:
                for i in invoice:
                    invoice_data = self.env['account.invoice'].browse(i)
                    invoice_data.signal_workflow('invoice_open')
            result['domain'] = str([('id','in',history_ids)])
            return result
