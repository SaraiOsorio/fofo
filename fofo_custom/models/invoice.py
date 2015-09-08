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
from openerp.exceptions import except_orm, Warning, RedirectWarning

class account_journal(models.Model):
    _inherit = 'account.journal'

    land_cost_journal = fields.Boolean('Landed Cost Journal', help='Check this box if you are creating laneded cost journal.')

class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    container_id = fields.Many2one('container.order', string="Related Container Order")
    is_shipper_invoice = fields.Boolean('Shipper Invoice', help='If this check box is ticked that will indicate the invoice is related to shipper.')
    allocate_land_cost = fields.Boolean('Allocate Landed Cost', help='If this check box is ticked that will indicate the landed cost will go to product and journal entry will be raised for landed cost.', readonly=True, states={'draft': [('readonly', False)]})
    landed_cost_journal_id = fields.Many2one('account.journal', string='Landed Cost Journal',
        required=False, readonly=True, states={'draft': [('readonly', False)]})
    stock_valuation_landcost_account = fields.Many2one('account.account', string='Stock Valuation Account',#TODO remove.
        required=False, domain=[('type', 'not in', ['view', 'closed'])],
        help="The stock valuation account for landed cost entry.", readonly=True, states={'draft': [('readonly', False)]})#TODO remove.
    expense_landcost_account = fields.Many2one('account.account', string='Expense Account',
        required=False, domain=[('type', 'not in', ['view', 'closed'])],
        help="The expense account for landed cost entry.", readonly=True, states={'draft': [('readonly', False)]}) #TODO remove.
    move_landed_cost_id = fields.Many2one('account.move', string='Journal Entry - Landed Cost',
        readonly=True, index=True, ondelete='restrict', copy=False,
        help="Link to the automatically generated Journal Items for landed cost.")


    @api.one
    def create_move_landed_cost(self, landed_cost_journal, stock_valuation_landcost_account, expense_landcost_account):
        #Note: Actually, I think we don't need these fields at all (but it is fine to have it invisibly but must auto default, so what??), because,
        #(see above, I updated sample) the CR in logistic journal, are always the same account as the DR on purchase journal (whatever the account is, in this case, 51200, 51201, 51202, it will be even out line by line)
        #the DR in logistic journal, at first I want to get from Stock Valuation account in Product Category, but may be not good, as Product Lines can be different products. SO -> let's use the DR account from the Landed Cost Journal master data itself, WDYT?        
        period_obj = self.env['account.period']
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        currency_obj = self.env['res.currency']
        created_move_ids = []
        
        if not self.period_id:
            period_ids = period_obj.find(self.date_invoice)
        else:
            period_ids = [self.period_id.id]
        company_currency = self.company_id.currency_id
        current_currency = self.currency_id
        ctx = dict(self._context or {})
        ctx.update({'date': self.date_invoice})
        amount = current_currency.compute(self.amount_untaxed, company_currency)
        
        if landed_cost_journal.type == 'purchase':
            sign = 1
        else:
            sign = 1#TODO check
        move_name = self.name or self.number
        reference = self.name or self.number
        move_vals = {
            'name': '/',
            'date': self.date_invoice,
            'ref': reference,
            'period_id': period_ids and period_ids[0] or False,
            'journal_id': landed_cost_journal.id,
        }
        move_id = move_obj.create(move_vals)
        journal_id = landed_cost_journal.id
        partner_id = self.partner_id.id
        for line in self.invoice_line:
            move_line_obj.create({
                'name': move_name,
                'ref': reference,
                'move_id': move_id.id,
                'account_id': line.account_id.id,
                'debit': 0.0,
                'credit': line.price_subtotal,#amount,
                'period_id': period_ids and period_ids[0] or False,
                'journal_id': journal_id,
                'partner_id': partner_id,
                'currency_id': company_currency.id <> current_currency.id and current_currency.id or False,
                'amount_currency': company_currency.id <> current_currency.id and -sign * self.amount_untaxed or 0.0,
                'date': self.date_invoice,
                #'analytic_account_id' : ?,
            })
        move_line_obj.create({
            'name': move_name,
            'ref': reference,
            'move_id': move_id.id,
            'account_id': landed_cost_journal.default_debit_account_id.id, #expense_landcost_account.id,
            'credit': 0.0,
            'debit': amount,
            'period_id': period_ids and period_ids[0] or False,
            'journal_id': journal_id,
            'partner_id': partner_id,
            'currency_id': company_currency.id <> current_currency.id and  current_currency.id or False,
            'amount_currency': company_currency.id <> current_currency.id and sign * self.amount_untaxed or 0.0,
            #'analytic_account_id': ?,
            'date': self.date_invoice,
        })
        self.write({'move_landed_cost_id': move_id.id})
        created_move_ids.append(move_id.id)
        return True

    @api.multi
    def action_move_create(self):
        res = super(account_invoice, self).action_move_create()
        for inv in self:
            if inv.container_id:

                #Create journal entry for landed cost. Issue: 3190 - 6 Sep 2015
                if inv.allocate_land_cost:
                    if not inv.landed_cost_journal_id:
                        raise Warning(('Error!'), _('Please define landed cost journal to create landed cost journal entry.'))
                    if not inv.landed_cost_journal_id.default_debit_account_id:
                        raise Warning(('Error!'), _('Please define debit account on landed cost journal to create landed cost journal entry.'))
                    inv.create_move_landed_cost(inv.landed_cost_journal_id, inv.stock_valuation_landcost_account, inv.expense_landcost_account)

                #Write landed cost on product form:
'''                if inv.allocate_land_cost:
                    if inv.container_id.total_volume > 0:
                        ship_cost_by_volume = inv.amount_total / inv.container_id.total_volume #do computation here same like function field on shiping_cost_by_volumne on CO object.
                    else:
                        ship_cost_by_volume = inv.amount_total #TODO check.. is this correct is container has no volume then we consider to skip that.? 
                    for co_line in inv.container_id.co_line_ids:
                        #Update landed cost on product form by volume. Ref: issues/3188 Date: 6 Sep 2015 => Here are we making average landed cost each time so we divide by two.
                        if co_line.product_id.landed_cost > 0.0:
                            #landed_cost = co_line.product_id.landed_cost + ((co_line.container_order_id.shipping_cost_by_volume * co_line.volume) / co_line.product_qty) / 2
                            landed_cost = (co_line.product_id.landed_cost + ((ship_cost_by_volume * co_line.volume) / co_line.product_qty)) / 2
                        else:# First time update on product form.
                            if co_line.product_qty > 0.0:
                                #landed_cost = (co_line.container_order_id.shipping_cost_by_volume * co_line.volume) / co_line.product_qty
                                landed_cost = (ship_cost_by_volume * co_line.volume) / co_line.product_qty
                        co_line.product_id.write({'landed_cost': landed_cost}) '''

                # set CO to done if all ivnoices are validated.
                flag = True
                for i in inv.container_id.invoice_ids:
                    if i.id != inv.id and i.state == 'draft':
                        flag = False
                if flag and inv.container_id.invoice_shipper:
                    inv.container_id.action_done()
        return res

