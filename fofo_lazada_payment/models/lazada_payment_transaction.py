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

class lazada_payment_transaction_type(models.Model):
    _name = 'lazada.payment.transaction.type'
    
    name = fields.Char('Name', required=True)
    

class lazada_payment_transaction_config(models.Model):
    _name = 'lazada.payment.transaction.config'
    
    transaction_type_id = fields.Many2one('lazada.payment.transaction.type', string='Transaction Type', required=True)
    account_id = fields.Many2one('account.account', string='Related Account')
    state_to_skip = fields.Boolean('Transaction Type to Ignore', help='Tick this box if you do not want to force order reference while importing csv.')
    transaction_type_name = fields.Char(related='transaction_type_id.name', string="Transaction Type Name")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
