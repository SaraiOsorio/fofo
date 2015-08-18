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

from openerp.osv import osv

class purchase_order(models.Model):
    _inherit = "purchase.order"

    def init(self, cr):
        self.READONLY_STATES.update({'contained': [('readonly', True)], 'cancel': [('readonly', True)]}    )
    READONLY_STATES_CON = {
        'confirmed': [('readonly', True)],
        'approved': [('readonly', True)],
        'done': [('readonly', True)],
        'contained': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    STATE_SELECTION = [
        ('draft', 'Draft PO'),
        ('sent', 'RFQ'),
        ('bid', 'Bid Received'),
        ('confirmed', 'Waiting Approval'),
        ('approved', 'Purchase Confirmed'),
        ('contained', 'Contained'),#new
        ('except_picking', 'Shipping Exception'),
        ('except_invoice', 'Invoice Exception'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ]

    #Override from purchase module only to forcefully cancel PO if its related to purchase_by_container....
    @api.v7
    def action_cancel(self, cr, uid, ids, context=None):
        res = super(purchase_order, self).action_cancel(cr, uid, ids, context)
        purchase = self.browse(cr, uid, ids, context)[0]
        if purchase.purchase_by_container:
            for co in purchase.container_ids:
                if co.state not in ('cancel'):
                    raise osv.except_osv(
                        _('Unable to cancel this purchase order.'),
                        _('You must first cancel all container orders related to this purchase order.'))
            self.write(cr, uid, ids, {'state': 'cancel'}, context=context)#Forecefully cancel for container case. Ref: def wkf_action_cancel(....) Bug #3080
            self.set_order_line_status(cr, uid, ids, 'cancel', context=context)
        return res
        
    @api.v7
    def picking_done(self, cr, uid, ids, context=None):#todo remove this.
        #DO NOT ALLOW PURCHASE ORDER TO BE RECEIVED IF PO IS TYPE OF CONTAINER ORDER. CHECK IF ALL CONTAINER ORDERS ARE DONE THAN ONLY RECEIVED...
        for purchase in self.browse(cr, uid, ids, context=context):
            if not purchase.purchase_by_container:#Ecosoft
                self.write(cr, uid, [purchase.id], {'shipped':1,'state':'approved'}, context=context)
            else:#Ecosoft
                if purchase.order_line:#Ecosoft
                    shipped = True#Ecosoft
                    for line in purchase.order_line:#Ecosoft
                        if line.remain_contain_qty > 0.0:#Ecosoft
                            shipped = False#Ecosoft
                    self.write(cr, uid, [purchase.id], {'shipped': shipped,'state':'approved'}, context=context)#Ecosoft

        # Do check on related procurements:
        proc_obj = self.pool.get("procurement.order")
        po_lines = []
        for po in self.browse(cr, uid, ids, context=context):
            po_lines += [x.id for x in po.order_line]
        if po_lines:
            procs = proc_obj.search(cr, uid, [('purchase_line_id', 'in', po_lines)], context=context)
            if procs:
                proc_obj.check(cr, uid, procs, context=context)
        self.message_post(cr, uid, ids, body=_("Products received"), context=context)
        return True

    @api.multi
    def picking_done(self):
        #DO NOT ALLOW PURCHASE ORDER TO BE RECEIVED IF PO IS TYPE OF CONTAINER ORDER. CHECK IF ALL CONTAINER ORDERS ARE DONE THAN ONLY RECEIVED...
        for purchase in self:
            if not purchase.purchase_by_container:#Ecosoft
                self.write({'shipped':1,'state':'approved'})
            else:#Ecosoft
                if purchase.order_line:#Ecosoft
                    shipped = True#Ecosoft
                    for line in purchase.order_line:#Ecosoft
                        if line.remain_contain_qty > 0.0:#Ecosoft
                            shipped = False#Ecosoft
                    self.write({'shipped': shipped,'state':'approved'})#Ecosoft

        # Do check on related procurements:
        proc_obj = self.env["procurement.order"]
        po_lines = []
        for po in self:
            po_lines += [x.id for x in po.order_line]
        if po_lines:
            procs = proc_obj.search([('purchase_line_id', 'in', po_lines)])
            if procs:
                proc_obj.check(procs)
        self.message_post(body=_("Products received"))
        return True

    @api.one
    @api.depends('order_line','order_line.state')
    def _check_line_state(self):
        if not self.purchase_by_container:
            self.is_contained = False
        else:
            self.is_contained = True
            for line in self.order_line:
                if line.state != 'contained' and line.state != 'done':
                    self.is_contained = False
            if self.is_contained:
                self.signal_workflow('purchase_contained')

    @api.v7
    def has_stockable_product(self, cr, uid, ids, *args):#todo: remove
        if not order.purchase_by_container:
            for order in self.browse(cr, uid, ids):
                for order_line in order.order_line:
                    if order_line.product_id and order_line.product_id.type in ('product', 'consu'):
                        return True
        else:
            return False
        return False

    @api.model
    def has_stockable_product(self):
        if not self.purchase_by_container:
            for order in self:
                for order_line in order.order_line:
                    if order_line.product_id and order_line.product_id.type in ('product', 'consu'):
                        return True
        else:
            return False
        return False

    @api.multi#todo check
    def wkf_order_contained(self):
        self.write({'state': 'contained'})

    @api.one
    @api.depends('state', 'order_line', 'order_line.state', 'order_line.remain_contain_qty', 'order_line.contained_qty')
    def _get_contain_ids(self):
        container_ids = []
        if self.purchase_by_container:
            container_ids = []
            for line in self.order_line:
                for x in line.co_line_ids:
                    container_ids.append(x.container_order_id.id)
        if container_ids:
            self.container_ids = container_ids

    @api.multi
    @api.depends('container_ids', 'purchase_by_container')
    def _count_all(self):
        self.container_count = len(self.container_ids)

    @api.multi
    def force_done(self):
        self.state = 'done'

    @api.multi
    def container_open(self):
        container_ids = []
        for po in self:
            container_ids += [co.id for co in po.container_ids]
        result = self.env.ref('fofo_custom.container_order_action')
        result = result.read()[0]
        result['context'] = {}
        if len(container_ids) > 1:
            result['domain'] = "[('id','in', [" + ','.join(map(str, container_ids)) + "])]"
        else:
            result['domain'] = "[('id','in', [" + ','.join(map(str, container_ids)) + "])]"
        return result

    @api.one
    @api.constrains('order_line', 'purchase_by_container')
    def _check_order_line_service(self):
        if self.purchase_by_container:
            for line in self.order_line:
                if line.product_id  and line.product_id.type == 'service':
                    raise Warning (_('Error!'), ('You cannot create purchase order with Purchase by Container option if one of purchase order line has service type product.'))
        return True

    purchase_by_container = fields.Boolean('Purchase by Container', default=True, help="Tick this box is you want to purchase items by container order.", states=READONLY_STATES_CON)
    is_contained = fields.Boolean('Contained', readonly=True, compute='_check_line_state', help="Check box will be automatically ticked if all purchase order lines are contained by container order.", copy=False)
    state = fields.Selection(STATE_SELECTION)#added contained status.
    container_ids =  fields.Many2many('container.order', 'purchase_contain_rel', 'purchase_id', 'container_id', compute=_get_contain_ids, string='Container List', store=True, copy=False, readonly=True)
    container_count = fields.Integer(compute=_count_all, string='Container Counts', copy=False, readonly=True)


    # Added readonly=True for contained status so override fields as below.
    picking_type_id = fields.Many2one(states= {'contained': [('readonly', True)], 'confirmed': [('readonly', True)], 'approved': [('readonly', True)], 'done': [('readonly', True)], 'cancel':[('readonly',True)]})
    date_order = fields.Datetime(states={'confirmed':[('readonly',True)],'contained':[('readonly',True)],
                                                                      'approved':[('readonly',True)], 'cancel':[('readonly',True)]})
    company_id =  fields.Many2one(states={'contained':[('readonly',True)],'confirmed': [('readonly', True)], 'approved': [('readonly', True)], 'cancel':[('readonly',True)]})
    partner_ref =  fields.Char( states={'contained':[('readonly',True)], 'confirmed':[('readonly',True)],
                                                                 'approved':[('readonly',True)],
                                                                 'done':[('readonly',True)], 'cancel':[('readonly',True)]},)
    order_line = fields.One2many( states={'contained':[('readonly',True)],'approved':[('readonly',True)],
                                              'done':[('readonly',True)], 'cancel':[('readonly',True)]},
                                      )

class purchase_order_line(models.Model):
    _inherit = "purchase.order.line"
    
    @api.multi
    def name_get(self):
        res = []
        for record in self:
            desc = record.product_id.name
            if record.product_id.description_purchase:
                desc = record.product_id.description_purchase
            name = record.order_id.name + ' / ' + desc
            res.append((record.id, name))
        return res
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('product_id.name', operator, name)] + args, limit=limit)
        if not recs:
            recs = self.search([('order_id.name', operator, name)] + args, limit=limit)
        return recs.name_get()
    
    state = fields.Selection([('draft', 'Draft'), 
                              ('confirmed', 'Confirmed'), 
                              ('contained', 'Contained'), 
                              ('done', 'Done'), 
                              ('cancel', 'Cancelled')],
                            'Status', required=True, readonly=True, copy=False,
                             help=' * The \'Draft\' status is set automatically when purchase order in draft status. \
                                       \n* The \'Confirmed\' status is set automatically as confirm when purchase order in confirm status. \
                                       \n* The \'Contained\' status is set automatically when purchase order is set as contained. \
                                       \n* The \'Done\' status is set automatically when purchase order is set as done. \
                                       \n* The \'Cancelled\' status is set automatically when user cancel purchase order.')
    #container_id = fields.Many2one('container.order')
    purchase_by_container = fields.Boolean(related='order_id.purchase_by_container', string='Purchase by Container', store=True)

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        #Show only confirmed purchase order lines + Purchase by Container =True on container order form. Get context and set args.
        if self.env.context.get('only_confirmed', False):
            if self.env.context.get('co_line_ids', False):
                skip_po_line_ids = []
                for co_line in self.env.context['co_line_ids']:
                    if len(co_line) > 1:
                        if co_line[2] and co_line[2].get('po_line_id', False):
                            skip_po_line_ids.append(co_line[2]['po_line_id'])
                        elif co_line[2] and not co_line[2].get('po_line_id', False):
                            co_line_data = self.env['container.order.line'].browse(co_line[1])
                            skip_po_line_ids.append(co_line_data.po_line_id.id)
                        elif not co_line[2] and co_line[1]:
                            co_line_data = self.env['container.order.line'].browse(co_line[1])
                            skip_po_line_ids.append(co_line_data.po_line_id.id)
                        else:
                            pass
                if skip_po_line_ids:
                    args.append(['id', 'not in', skip_po_line_ids])#CO: Purchase order line - please list only UNContained + Selected item on current CO - Issue Bug #2789
            args.append(['state', '=', 'confirmed'])
            args.append(['remain_contain_qty', '>', 0.0])
            args.append(['purchase_by_container', '=', True])
        return super(purchase_order_line, self).search(args, offset=offset, limit=limit, order=order, count=count)

    @api.v7
    def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
            name=False, price_unit=False, state='draft', context=None):
        res = super(purchase_order_line, self).onchange_product_id(cr, uid, ids, pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=date_order, fiscal_position_id=fiscal_position_id, date_planned=date_planned,
            name=name, price_unit=price_unit, state=state, context=context)
        res_partner = self.pool.get('res.partner')
        product_product = self.pool.get('product.product')
        product_uom = self.pool.get('product.uom')
        context_partner = context.copy()
        if partner_id:
            lang = res_partner.browse(cr, uid, partner_id).lang
            context_partner.update( {'lang': lang, 'partner_id': partner_id} )
        product = product_product.browse(cr, uid, product_id, context=context_partner)
        if product.description_purchase:
            name = product.description_purchase
            res['value'].update({'name': name})
        return res

    @api.one
    @api.depends('product_packaging','product_qty','product_id', 'state')
    def _compute_volume(self):
        self.volume = 0.0
        self.weight = 0.0
        if self.product_packaging:
            self.volume = self.product_packaging.volume * self.product_qty
            self.weight = self.product_packaging.weight_gross * self.product_qty
        else:
            self.volume = self.product_id.volume * self.product_qty
            self.weight = self.product_id.weight * self.product_qty

    @api.one
    @api.depends('product_packaging','product_id', 'product_qty', 'state')
    def _number_packages(self):
        self.number_packages = 0
        for line in self:
            try:
                self.number_packages = int((line.product_qty+line.qty_package-0.0001) / line.qty_package)
            except:
                self.number_packages = 0

    @api.one
    @api.depends('co_line_ids','co_line_ids.product_qty', 'co_line_ids.state', 'state', 'product_qty', 'product_id', 'order_id.state', 'move_ids', 'move_ids.state')
    def _contained_qty(self):
        self.contained_qty = 0.0
        self.remain_contain_qty = self.product_qty
        contain_qty = 0.0
        cancel_qty = 0.0
        for co in self.co_line_ids:
            if co.state == 'confirmed' or co.state == 'done':
                if co.move_ids:
                    for move in co.move_ids:
                        if move.state != 'cancel':# Fix for: Cancelled IN does not add back its Quantity for next CO - Bug #3105
                            contain_qty += co.product_qty
                        else:
                            contain_qty += co.product_qty
                            cancel_qty += move.product_uom_qty
                else:
                    contain_qty += co.product_qty
        contain_qty = contain_qty - cancel_qty
        self.contained_qty = contain_qty
        self.remain_contain_qty = self.product_qty - self.contained_qty

    @api.one
    @api.depends('co_line_ids','co_line_ids.product_qty', 'co_line_ids.state', 'product_qty', 'state', 'product_id', 'order_id.state')
    def _contained_qty_draft(self):
        self.contained_qty_draft = 0.0
        contained_qty_draft = 0.0
        for co in self.co_line_ids:
            if co.state == 'draft':
                contained_qty_draft += co.product_qty
        self.contained_qty_draft = contained_qty_draft

    weight = fields.Float(string="Weight", digits=dp.get_precision('Account'), store=True, compute='_compute_volume')
    volume = fields.Float(string="Volume", digits=dp.get_precision('Account'), store=True, compute='_compute_volume')
    reference = fields.Char(related = 'order_id.name', string='PO number')
    purchase_by_container = fields.Boolean(related = 'order_id.purchase_by_container', string='Purchase by Container', store=True)
    supplier_id = fields.Many2one('res.partner', related='order_id.partner_id', string="Supplier")
    product_packaging =  fields.Many2one('product.packaging', string='Packaging')
    product_tmpl_id = fields.Many2one(related='product_id.product_tmpl_id', type='many2one', relation='product.template', string='Product Template')
    number_packages =  fields.Integer(compute=_number_packages, string='Total Number of Packages', store=True)
    qty_package = fields.Float(string='Quantity / Package',related='product_packaging.qty')
    co_line_ids = fields.One2many('container.order.line', 'po_line_id', string='Container Order Line')

    contained_qty =  fields.Float(compute=_contained_qty, string='Confirmed Contained Qty', store=True)
    contained_qty_draft =  fields.Float(compute=_contained_qty_draft, string='Draft Contained Qty', store=True)
    remain_contain_qty =  fields.Float(compute=_contained_qty, string='Remaining Contained Qty', store=True, help='Remaining qty to contain.')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
