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
from openerp.tools.translate import _
from openerp.osv import osv
from openerp.addons.account.report.account_financial_report import report_account_common

class report_account_common(report_account_common):
    
    def get_lines(self, data):
        result = super(report_account_common, self).get_lines(data)
        #if report for balance sheet then no need to do extra operations, just return super call
        if 'Balance Sheet' in  data['form']['account_report_id'][1]:
            return result
        
        operating_revenue = 0.0
        cost_of_goods = 0.0
        income = 0.0
        expense = 0.0
        
        for res in result:
            #find the balance of Operating Revenue Account
            if '400000' in res['name']:
                operating_revenue = res['balance']
            #find the balance of Cost of Good Sold  account Account
            if '510000' in res['name']:
                cost_of_goods = res['balance']
            #find the balance of Expense
            if res['name'] == 'Expense':
                expense = res['balance']
            #find the balance of Income
            if res['name'] == 'Income':
                income = res['balance']

        #Calculate the gross profit
        gross_profit = operating_revenue - cost_of_goods
        #calculate the net profit
        net_profit = income - expense
        
        #find the list index of  Cost of Good Sold  account
        try:
            cogs_index = [i for i,a in enumerate(result) if '510000' in a['name']][0]
        except:
            cogs_index = False
        
        if cogs_index:
            #get the level of  Cost of Good Sold  account
            cogs_level = result[cogs_index]['level']
            
            cogs_lst_child_index = cogs_index
            for r in result[cogs_index + 1:]:
                if r['level'] == cogs_level:
                    #find the next account which contains the same level of  Cost of Good Sold account
                    cogs_lst_child_index = [i for i,a in enumerate(result) if r['name'] == a['name']][0]
                    continue
            #insert the gross profit record after the  Cost of Good Sold's last child
            result.insert(cogs_lst_child_index, {'account_type': 'view', 
                         'balance': gross_profit,
                         'balance_cmp': gross_profit, 
                         'type': 'account', 
                         'name': 'Gross Profit', 
                         'level': 1})
        
        result.append({'account_type': False, 
                       'balance': net_profit, 
                       'balance_cmp': net_profit,
                       'type': 'report', 
                       'name': 'Net Profit', 
                       'level': 1})
        return result

class report_financial(osv.AbstractModel):
    _name = 'report.account.report_financial'
    _inherit = 'report.abstract_report'
    _template = 'account.report_financial'
    _wrapped_report_class = report_account_common
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: