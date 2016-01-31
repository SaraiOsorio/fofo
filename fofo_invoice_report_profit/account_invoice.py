# -*- encoding: utf-8 -*-
##############################################################################
#
#    Account Invoice Margin module for Odoo
#    Copyright (C) 2015 Akretion (http://www.akretion.com)
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
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

from openerp import models, api


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.model
    def create(self, vals):
        res = super(AccountInvoiceLine, self).create(vals)
        # Re-Calculate with FOFO's cost
        if vals.get('product_id'):
            pp = self.env['product.product'].browse(vals['product_id'])
            std_price = pp.total_cost_call  # FOFO price
            inv_uom_id = vals.get('uos_id')
            if inv_uom_id and inv_uom_id != pp.uom_id.id:
                std_price = self.env['product.uom']._compute_price(
                    pp.uom_id.id, std_price, inv_uom_id)
        # Update cost
        res.standard_price_company_currency = std_price
        return res

    @api.multi
    def write(self, vals):
        res = super(AccountInvoiceLine, self).write(vals)
        # Re-Calculate with FOFO's cost
        if not vals:
            vals = {}
        if 'product_id' in vals or 'uos_id' in vals:
            for il in self:
                if 'product_id' in vals:
                    if vals.get('product_id'):
                        pp = self.env['product.product'].browse(
                            vals['product_id'])
                    else:
                        pp = False
                else:
                    pp = il.product_id or False
                # uos_id is NOT a required field
                if 'uos_id' in vals:
                    if vals.get('uos_id'):
                        inv_uom = self.env['product.uom'].browse(
                            vals['uos_id'])
                    else:
                        inv_uom = False
                else:
                    inv_uom = il.uos_id or False
                std_price = 0.0
                if pp:
                    std_price = pp.total_cost_call  # FOFO price
                    if inv_uom and inv_uom != pp.uom_id:
                        std_price = self.env['product.uom']._compute_price(
                            pp.uom_id.id, std_price, inv_uom.id)
                il.write({'standard_price_company_currency': std_price})
        return res
