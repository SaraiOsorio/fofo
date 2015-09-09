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

class account_invoice_refund(models.TransientModel):
    _inherit = 'account.invoice.refund'
    
    is_lazada_order = fields.Boolean('Lazada Order?', readonly=True)
    lazada_order_no = fields.Char('Lazada Order Number', readonly=False)
    
    @api.v7
    def compute_refund(self, cr, uid, ids, mode='refund', context=None):
        res = super(account_invoice_refund, self).compute_refund(cr, uid, ids, mode='refund', context=context)
        inv_obj = self.pool.get('account.invoice')
        new_inv_id = res['domain'][1][2]
        old_inv_id = context.get('active_id', False)
        old_inv_data = inv_obj.browse(cr, uid, old_inv_id, context=context)
        inv_obj.write(cr, uid, new_inv_id, {'is_lazada_order': old_inv_data.is_lazada_order,
                                            'lazada_order_no' : old_inv_data.lazada_order_no})
        return res
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: